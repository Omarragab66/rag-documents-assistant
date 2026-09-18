import re

import ollama
from app.core.config import settings
from app.services.retrieval import extract_code_blocks, retrieval_service

class GenerationService:
    def __init__(self):
        self.client = None

    def initialize(self):
        if self.client is None:
            self.client = ollama.Client(host=settings.OLLAMA_HOST)

    def build_prompt(self, question: str, docs: list[str], metas: list[dict]) -> str:
        context_parts = []
        for doc, meta in zip(docs, metas):
            source = meta.get("source", "unknown")
            chunk_idx = meta.get("chunk_index", 0)
            context_parts.append(f"[{source} (chunk {chunk_idx})]:\n{doc}")
        
        context_text = "\n\n".join(context_parts)
        prompt = (
            "You are an expert FastAPI technical documentation assistant.\n"
            "The documentation context below contains relevant information for most questions. Read it carefully before deciding information is unavailable.\n"
            "Answer using ONLY facts explicitly present in the documentation context.\n"
            "Explain the answer in plain text only, using 2-4 concise sentences.\n"
            "Do not write code, imports, decorators, function names, or code blocks.\n"
            "Never invent or rename technical identifiers.\n"
            "Only reply with 'I do not have enough information in the provided documentation.' if the context truly does not mention the topic at all.\n\n"
            f"Documentation Context:\n{context_text}\n\n"
            f"User Question: {question}\n\n"
            "Helpful and Grounded Answer:"
        )
        return prompt

    def answer_is_supported(self, answer: str, docs: list[str]) -> bool:
        refusal = "I do not have enough information in the provided documentation."
        if answer == refusal:
            return True

        context = "\n".join(docs).lower()
        api_tokens = re.findall(
            r"@\w+\.\w+|\b(?:FastAPI|APIRouter|Depends|Query|CORSMiddleware|"
            r"BackgroundTasks|JSONResponse|OAuth2PasswordBearer|"
            r"OAuth2PasswordRequestForm)\b",
            answer,
        )
        if any(token.lower() not in context for token in api_tokens):
            return False

        stop_words = {"the", "and", "for", "with", "from", "this", "that", "are", "can", "use", "you"}
        answer_terms = {
            term for term in re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", answer.lower())
            if len(term) > 3 and term not in stop_words
        }
        context_terms = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", context))
        overlap = len(answer_terms & context_terms) / max(len(answer_terms), 1)
        return overlap >= 0.35

    def answer_query(self, question: str, top_k: int = 3) -> dict:
        self.initialize()
        docs, metas = retrieval_service.retrieve(question, top_k=top_k)
        prompt = self.build_prompt(question, docs, metas)
        response = self.client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.0, "num_predict": 220, "repeat_penalty": 1.3}
        )
        raw_answer = response["message"]["content"].strip()
        refusal = "I do not have enough information in the provided documentation."
        if raw_answer != refusal and not self.answer_is_supported(raw_answer, docs):
            raw_answer = refusal

        if raw_answer != refusal:
            code_block = next(
                (block for doc in docs for block in extract_code_blocks(doc)),
                None,
            )
            if code_block is not None:
                raw_answer += f"\n\n```python\n{code_block}```"
        sources = sorted(list({meta.get("source", "unknown") for meta in metas}))
        
        return {
            "answer": raw_answer,
            "sources": sources
        }

generation_service = GenerationService()
