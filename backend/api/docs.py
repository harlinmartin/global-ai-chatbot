"""
Document management API — Phase 3.

Endpoints (all JWT-protected, workspace owner only):
  POST   /api/docs/upload              — upload a file, trigger processing
  GET    /api/docs/?workspace_id=...   — list documents for a workspace
  DELETE /api/docs/{doc_id}            — delete doc + chunks from PG + Qdrant
"""

from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from auth.security import get_current_user
from auth.models import User
from chat.models import Workspace, Document, DocumentChunk
from docs import processor, qdrant_service

router = APIRouter(prefix="/api/docs", tags=["docs"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_workspace_for_owner(
    workspace_id: str,
    user: User,
    db: AsyncSession,
) -> Workspace:
    """Return the workspace if it exists and is owned by the requesting user."""
    result = await db.execute(
        select(Workspace).filter(
            Workspace.id == workspace_id,
            Workspace.owner_id == user.id,
        )
    )
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found or access denied")
    return ws


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file (PDF / TXT / MD) and trigger the extract→chunk→embed pipeline.
    Returns immediately with the Document record; processing runs synchronously.
    """
    # Validate workspace ownership
    await _get_workspace_for_owner(workspace_id, current_user, db)

    # Validate file extension
    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # Create Document row in "pending" state
    doc = Document(
        workspace_id=workspace_id,
        filename=filename,
        status="pending",
        file_size_bytes=len(content),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Run the processing pipeline (synchronous in this request — keeps it simple).
    # A processing failure (e.g. an empty/blank PDF with no extractable text) must
    # not 500 the request — the pipeline already records doc.status="failed", so we
    # swallow the exception here and return the document with its failed status.
    try:
        await processor.process_document(
            doc_id=str(doc.id),
            workspace_id=workspace_id,
            filename=filename,
            content=content,
            db=db,
        )
    except Exception:
        pass

    # Refresh after processing to get updated status/chunk_count
    await db.refresh(doc)
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "file_size_bytes": doc.file_size_bytes,
        "error": doc.error,
    }


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@router.get("/")
async def list_documents(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents for a workspace (owner only)."""
    await _get_workspace_for_owner(workspace_id, current_user, db)

    result = await db.execute(
        select(Document)
        .filter(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "chunk_count": d.chunk_count,
            "file_size_bytes": d.file_size_bytes,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document, all its PG chunks, and its Qdrant vectors."""
    # Fetch the document
    result = await db.execute(select(Document).filter(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Verify ownership via workspace
    await _get_workspace_for_owner(str(doc.workspace_id), current_user, db)

    # Delete Qdrant vectors for this document
    try:
        qdrant_service.delete_by_document(str(doc.workspace_id), doc_id)
    except Exception:
        pass  # Don't block deletion if Qdrant is temporarily down

    # Delete PG rows (chunks cascade from document FK)
    await db.delete(doc)
    await db.commit()

    return {"status": "deleted", "id": doc_id}
