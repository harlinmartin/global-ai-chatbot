import asyncio
from database import engine
from auth.models import Base
import chat.models # To register models
import auth.models # To register models

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created!")

if __name__ == "__main__":
    asyncio.run(init_db())
