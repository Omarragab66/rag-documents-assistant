import os
import re

import chromadb
from chromadb.utils import embedding_functions
from app.core.config import settings


def extract_code_blocks(text: str) -> list[str]:
    """Return fenced code blocks exactly as they appear in source text."""
    return re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)

class RetrievalService:
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_fn = None

    def initialize(self):
        if self.collection is not None:
            return
        
        self.client = chromadb.PersistentClient(path=settings.VECTOR_STORE_DIR)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
        self.collection = self.client.get_collection(
            name=settings.COLLECTION_NAME,
            embedding_function=self.embedding_fn
        )

    def retrieve(self, query: str, top_k: int = 3):
        if self.collection is None:
            self.initialize()
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        return docs, metas

retrieval_service = RetrievalService()
