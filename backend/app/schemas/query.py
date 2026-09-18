from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, description="The technical question to ask the document assistant", examples=["How do I handle CORS in FastAPI?"])

class QueryResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer synthesized from documentation")
    sources: list[str] = Field(default_factory=list, description="List of source documentation files cited")
