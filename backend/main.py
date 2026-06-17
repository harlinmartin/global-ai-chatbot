from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router
from api.health import router as health_router
from config import settings

app = FastAPI(title="AI Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])


@app.get("/")
async def root():
    return {"message": "AI Chatbot API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.backend_port, reload=True)
