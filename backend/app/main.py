from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.retrieval import retrieval_service
from app.services.generation import generation_service
from app.api.routes.query import router as query_router
from app.utils.logging_config import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing RAG resources at application startup...")
    retrieval_service.initialize()
    generation_service.initialize()
    logger.info("RAG vector store and LLM service ready.")
    yield
    logger.info("Shutting down RAG application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Full RAG Document Assistant for FastAPI Technical Documentation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, tags=["RAG Assistant"])
app.include_router(query_router, prefix=settings.API_V1_STR, tags=["API v1"])
