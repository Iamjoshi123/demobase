"""FastAPI application entry point for Agentic Demo Brain."""

import asyncio
import sys

# Windows requires ProactorEventLoop for subprocess support (Playwright)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.api import workspaces, documents, credentials, recipes, policies, sessions, analytics, retrieval
from app.v2 import api as meetings_v2

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Agentic Demo Brain API")
    create_db_and_tables()
    logger.info(f"Database initialized: {settings.database_url}")
    logger.info(f"Voice enabled: {settings.enable_voice}")
    logger.info(f"Browser headless: {settings.playwright_headless}")
    yield
    logger.info("Shutting down Agentic Demo Brain API")


app = FastAPI(
    title="Agentic Demo Brain",
    description="AI-powered live product demo engine for B2B SaaS",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(workspaces.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(credentials.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(retrieval.router, prefix="/api")
app.include_router(meetings_v2.router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "Agentic Demo Brain",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
