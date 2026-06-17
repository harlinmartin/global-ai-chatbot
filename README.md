# AI Chatbot

Embeddable AI Chat Assistant — powered by Groq + Next.js + FastAPI.

## Running Locally

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
npm run dev -- --port 3001
```

Open http://localhost:3001

## Environment
Copy `backend/.env.example` to `backend/.env` and fill in your Groq API key.
