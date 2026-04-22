"""
TalkToDoctor — FastAPI Backend Entry Point

Voice-first AI medical intake system.
This server accepts patient audio, transcribes it, extracts
structured medical data, and serves it to doctors.

IMPORTANT: The AI NEVER diagnoses. It ONLY assists, extracts,
and summarizes. The doctor is the final authority.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.routers.intake import router as intake_router
from backend.routers.conversation import router as conversation_router
from backend.routers.doctor import router as doctor_router
from backend.routers.patient import router as patient_router
from backend.routers.report import router as report_router
from backend.routers.analytics import router as analytics_router
from backend.routers.integrations import router as integrations_router

# ──────────────────────────────────────────────
# Load environment variables
# ──────────────────────────────────────────────
load_dotenv()

# ──────────────────────────────────────────────
# Logging configuration
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Application lifespan
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🩺 TalkToDoctor backend starting up...")
    logger.info("   AI assists, doctor decides.")
    yield
    logger.info("🩺 TalkToDoctor backend shutting down.")


# ──────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────
app = FastAPI(
    title="TalkToDoctor API",
    description=(
        "Voice-first AI medical intake system. "
        "Accepts patient audio, transcribes via Whisper, "
        "extracts structured data via GPT-4. "
        "The AI NEVER diagnoses — the doctor is the final authority."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# CORS — allow the React frontend to connect
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternate dev port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.routers.queue import router as queue_router

# ──────────────────────────────────────────────
# Register routers
# ──────────────────────────────────────────────
app.include_router(intake_router, prefix="/api", tags=["Intake"])
app.include_router(conversation_router, prefix="/api", tags=["Conversation"])
app.include_router(doctor_router, prefix="/api", tags=["Doctor"])
app.include_router(patient_router, prefix="/api", tags=["Patient"])
app.include_router(report_router, prefix="/api", tags=["Report"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
app.include_router(integrations_router, prefix="/api", tags=["Integrations"])
app.include_router(queue_router, prefix="/api", tags=["Queue"])


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "TalkToDoctor API",
        "version": "0.2.0",
        "message": "AI assists, doctor decides."
    }
