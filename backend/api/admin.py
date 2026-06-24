from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Annotated
import uuid

from database import get_db
from chat.models import EvalLog, Workspace
from auth.models import User
from auth.security import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/evaluations")
async def get_dashboard_evaluations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    # Get user's workspace
    ws_result = await db.execute(select(Workspace).filter(Workspace.owner_id == current_user.id).limit(1))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    workspace_id = ws.id

    # Total queries
    total_result = await db.execute(select(func.count(EvalLog.id)).filter(EvalLog.workspace_id == workspace_id))
    total_queries = total_result.scalar() or 0

    # Average latency
    latency_result = await db.execute(select(func.avg(EvalLog.latency_ms)).filter(EvalLog.workspace_id == workspace_id))
    avg_latency = latency_result.scalar()
    avg_latency = float(avg_latency) if avg_latency else 0.0

    # Feedback counts
    up_result = await db.execute(select(func.count(EvalLog.id)).filter(EvalLog.workspace_id == workspace_id, EvalLog.feedback == 'up'))
    down_result = await db.execute(select(func.count(EvalLog.id)).filter(EvalLog.workspace_id == workspace_id, EvalLog.feedback == 'down'))
    up_votes = up_result.scalar() or 0
    down_votes = down_result.scalar() or 0
    
    total_votes = up_votes + down_votes
    positive_ratio = (up_votes / total_votes * 100) if total_votes > 0 else 0

    # Recent Feedback
    recent_feedback_result = await db.execute(
        select(EvalLog)
        .filter(EvalLog.workspace_id == workspace_id, EvalLog.feedback.is_not(None))
        .order_by(desc(EvalLog.created_at))
        .limit(10)
    )
    recent_feedback = recent_feedback_result.scalars().all()

    # Slow queries
    slow_queries_result = await db.execute(
        select(EvalLog)
        .filter(EvalLog.workspace_id == workspace_id, EvalLog.latency_ms.is_not(None))
        .order_by(desc(EvalLog.latency_ms))
        .limit(10)
    )
    slow_queries = slow_queries_result.scalars().all()

    # Coverage Gaps ("No Info" - defined here as empty retrieved chunks or fallback answers)
    no_info_result = await db.execute(
        select(EvalLog)
        .filter(
            EvalLog.workspace_id == workspace_id, 
            func.jsonb_array_length(EvalLog.retrieved_chunks) == 0
        )
        .order_by(desc(EvalLog.created_at))
        .limit(10)
    )
    no_info_queries = no_info_result.scalars().all()
    
    # Top Chunks
    # Since doing jsonb aggregations can be tricky, we'll fetch chunks and aggregate in Python
    all_logs_result = await db.execute(
        select(EvalLog.retrieved_chunks).filter(EvalLog.workspace_id == workspace_id)
    )
    all_chunks_lists = all_logs_result.scalars().all()
    
    chunk_counts = {}
    for chunks in all_chunks_lists:
        if not chunks:
            continue
        for chunk in chunks:
            # unique identifier for a chunk
            filename = chunk.get('filename', 'unknown')
            page = chunk.get('page')
            key = f"{filename} (Page {page})" if page else filename
            
            if key not in chunk_counts:
                chunk_counts[key] = {"filename": filename, "page": page, "count": 0}
            chunk_counts[key]["count"] += 1
            
    top_chunks = sorted(chunk_counts.values(), key=lambda x: x["count"], reverse=True)[:10]

    return {
        "metrics": {
            "total_queries": total_queries,
            "avg_latency_ms": round(avg_latency, 2),
            "up_votes": up_votes,
            "down_votes": down_votes,
            "positive_ratio": round(positive_ratio, 1)
        },
        "recent_feedback": [
            {
                "id": str(log.id),
                "question": log.question,
                "answer": log.answer,
                "feedback": log.feedback,
                "created_at": log.created_at.isoformat()
            } for log in recent_feedback
        ],
        "slow_queries": [
            {
                "id": str(log.id),
                "question": log.question,
                "latency_ms": log.latency_ms,
                "model_name": log.model_name,
                "created_at": log.created_at.isoformat()
            } for log in slow_queries
        ],
        "coverage_gaps": [
            {
                "id": str(log.id),
                "question": log.question,
                "created_at": log.created_at.isoformat()
            } for log in no_info_queries
        ],
        "top_chunks": top_chunks
    }

@router.get("/memories")
async def get_dashboard_memories(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    ws_result = await db.execute(select(Workspace).filter(Workspace.owner_id == current_user.id).limit(1))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    from chat.models import Memory
    memories_result = await db.execute(
        select(Memory).filter(Memory.workspace_id == ws.id).order_by(desc(Memory.created_at))
    )
    memories = memories_result.scalars().all()

    return {
        "memories": [
            {
                "id": str(m.id),
                "fact": m.fact,
                "created_at": m.created_at.isoformat()
            } for m in memories
        ]
    }

@router.delete("/memories/{memory_id}")
async def delete_dashboard_memory(
    memory_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    ws_result = await db.execute(select(Workspace).filter(Workspace.owner_id == current_user.id).limit(1))
    ws = ws_result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    from chat.models import Memory
    mem_result = await db.execute(
        select(Memory).filter(Memory.id == memory_id, Memory.workspace_id == ws.id)
    )
    mem = mem_result.scalar_one_or_none()
    
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    await db.delete(mem)
    await db.commit()
    
    return {"status": "ok"}
