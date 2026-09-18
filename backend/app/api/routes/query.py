from fastapi import APIRouter, HTTPException, status
from app.schemas.query import QueryRequest, QueryResponse
from app.services.generation import generation_service
from app.utils.logging_config import logger

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "ok",
        "service": "RAG Document Assistant Backend"
    }

@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
def query_documents(request: QueryRequest):
    try:
        logger.info(f"Processing query: {request.question}")
        result = generation_service.answer_query(request.question)
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"Error serving query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal pipeline error: {str(e)}"
        )
