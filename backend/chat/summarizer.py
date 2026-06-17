import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database import async_session_maker
from chat.models import Message, ChatSummary
from ai.factory import get_ai_provider

async def summarize_chat_background(chat_id: str):
    async with async_session_maker() as db:
        # Check if we have more than 30 messages
        result = await db.execute(
            select(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        if len(messages) <= 30:
            return

        # Check existing summary
        summary_result = await db.execute(
            select(ChatSummary)
            .filter(ChatSummary.chat_id == chat_id)
            .order_by(desc(ChatSummary.created_at))
            .limit(1)
        )
        latest_summary = summary_result.scalar_one_or_none()

        # Decide which messages to summarize
        # If we have a summary, we summarize the old summary + messages up to the current length - 10
        cutoff_index = len(messages) - 10
        messages_to_summarize = messages[:cutoff_index]
        last_message_summarized = messages_to_summarize[-1]

        if latest_summary and latest_summary.covers_through_message == last_message_summarized.id:
            # Already summarized up to this point
            return

        prompt = "Please summarize the following conversation concisely, focusing on key facts, user preferences, and important context that should be remembered for future interactions. "
        
        conversation_text = ""
        if latest_summary:
            conversation_text += f"Previous Summary: {latest_summary.summary}\n\n"
        
        for msg in messages_to_summarize:
            conversation_text += f"{msg.role.upper()}: {msg.content}\n"

        ai_messages = [
            {"role": "system", "content": "You are a highly efficient AI summarizer."},
            {"role": "user", "content": prompt + conversation_text}
        ]

        provider = get_ai_provider()
        summary_response = ""
        async for token in provider.stream(ai_messages):
            summary_response += token

        if summary_response:
            new_summary = ChatSummary(
                chat_id=chat_id,
                summary=summary_response,
                covers_through_message=last_message_summarized.id
            )
            db.add(new_summary)
            await db.commit()
