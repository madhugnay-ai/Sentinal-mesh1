from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=False)

from routes.gmail_oauth import router as gmail_oauth_router
from routes.workflows import router as workflows_router

app = FastAPI(title="SentinelMesh Studio API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows_router)
app.include_router(gmail_oauth_router)

app.state.gmail_token_path = ".gmail_tokens.json"


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
