import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from chat.models import WebsiteSource, Document
from docs.processor import process_document

async def fetch_and_clean_html(url: str, client: httpx.AsyncClient) -> tuple[str, str, list[str]]:
    """
    Fetch a URL, extract clean text, the page title, and a list of internal links.
    Returns: (clean_text, title, internal_links)
    """
    try:
        response = await client.get(url, follow_redirects=True, timeout=15.0)
        response.raise_for_status()
    except Exception:
        return "", "", []

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = soup.title.string if soup.title else url

    # Remove noisy tags
    for tag in soup(["nav", "footer", "header", "script", "style", "aside", "meta", "noscript"]):
        tag.decompose()

    # Extract text
    text = soup.get_text(separator="\n", strip=True)

    # Find internal links
    links = []
    base_domain = urlparse(url).netloc
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(url, href)
        parsed_full = urlparse(full_url)
        # Only keep same-domain http/https links, remove fragments
        if parsed_full.scheme in ["http", "https"] and parsed_full.netloc == base_domain:
            clean_url = f"{parsed_full.scheme}://{parsed_full.netloc}{parsed_full.path}"
            links.append(clean_url)

    return text, title, list(set(links))

async def crawl_website(source_id: str, db: AsyncSession):
    """
    Crawl a registered WebsiteSource up to depth 2.
    Clean the text and feed it into the RAG document processor.
    """
    # Fetch source
    result = await db.execute(select(WebsiteSource).filter(WebsiteSource.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        return

    source.status = "crawling"
    db.add(source)
    await db.commit()

    base_url = source.base_url
    workspace_id = source.workspace_id

    # Crawl queue: (url, depth)
    queue = [(base_url, 0)]
    visited = set()
    MAX_DEPTH = 2
    MAX_PAGES = 50  # Hard limit to prevent runaway crawling

    try:
        async with httpx.AsyncClient() as client:
            while queue and len(visited) < MAX_PAGES:
                current_url, depth = queue.pop(0)
                if current_url in visited:
                    continue
                
                visited.add(current_url)
                
                text, title, links = await fetch_and_clean_html(current_url, client)
                if text:
                    # Create a Document for this page
                    doc = Document(
                        workspace_id=workspace_id,
                        filename=current_url,
                        file_size_bytes=len(text.encode("utf-8")),
                        status="pending"
                    )
                    db.add(doc)
                    await db.commit()
                    await db.refresh(doc)
                    
                    # Process the document using the existing pipeline
                    await process_document(
                        doc_id=doc.id,
                        workspace_id=str(workspace_id),
                        filename=current_url,
                        content=text.encode("utf-8"),
                        db=db
                    )
                
                # Add new links if within depth
                if depth < MAX_DEPTH:
                    for link in links:
                        if link not in visited:
                            queue.append((link, depth + 1))
                            
        from sqlalchemy.sql import func
        source.status = "completed"
        source.last_crawled_at = func.now()
        db.add(source)
        await db.commit()

    except Exception as e:
        source.status = "failed"
        db.add(source)
        await db.commit()
        raise
