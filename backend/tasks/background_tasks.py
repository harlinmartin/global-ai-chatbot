import asyncio
import uuid
from celery_app import celery_app
from database import async_session_maker

@celery_app.task(name="tasks.background_tasks.crawl_task")
def crawl_task(source_id_str: str):
    """Celery task to run the async crawler."""
    from docs.crawler import crawl_website
    source_id = uuid.UUID(source_id_str)
    
    async def run_crawl():
        async with async_session_maker() as session:
            await crawl_website(source_id, session)

    asyncio.run(run_crawl())
    return f"Crawled source {source_id_str}"

@celery_app.task(name="tasks.background_tasks.memory_task")
def memory_task(user_message: str, workspace_id_str: str):
    """Celery task to run the async memory extractor."""
    from ai.memory_extractor import background_process_memory
    workspace_id = uuid.UUID(workspace_id_str)
    
    asyncio.run(background_process_memory(user_message, workspace_id))
    return "Memory processing complete"

@celery_app.task(name="tasks.background_tasks.summarize_task")
def summarize_task(chat_id_str: str):
    """Celery task to run chat summarization."""
    from chat.summarizer import summarize_chat_background
    
    asyncio.run(summarize_chat_background(chat_id_str))
    return f"Summarized chat {chat_id_str}"
