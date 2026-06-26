from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings

from api.health import router as health_router
from api.chat import router as chat_router
from api.auth import router as auth_router
from api.chats import router as chats_router
from api.messages import router as messages_router
from api.widget import router as widget_router
from api.docs import router as docs_router
from api.admin import router as admin_router

from contextlib import asynccontextmanager
from scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    
app = FastAPI(
    title="AI Chatbot Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/health")
app.include_router(chat_router, prefix="/api/chat")
app.include_router(auth_router)
app.include_router(chats_router)
app.include_router(messages_router, tags=["chat"])
app.include_router(widget_router, prefix="/api/widget")
app.include_router(docs_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "AI Chatbot API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.backend_port, reload=True)
