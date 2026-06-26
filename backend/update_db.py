import asyncio
from database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        try:
            await session.execute(text("ALTER TABLE chats ADD COLUMN is_human_handoff BOOLEAN DEFAULT FALSE;"))
            await session.commit()
            print("Added is_human_handoff to chats")
        except Exception as e:
            print(f"Error (maybe already exists): {e}")

asyncio.run(main())
