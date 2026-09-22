import re

import ollama
from app.core.config import settings
from app.services.retrieval import extract_code_blocks, retrieval_service


def _select_fallback_excerpt(query: str, docs: list[str], max_chars: int = 500) -> str:
    """Return the chunk most relevant to the query by keyword-overlap scoring.

    Mirrors the notebook's ``select_fallback_excerpt`` so that the backend and
    the notebook produce identical fallback behaviour when the grounding guard
    rejects the model's answer after two attempts.
    """
    stop_words = {
        "how", "what", "does", "can", "the", "for", "with", "from", "and", "in",
    }
    query_terms = {
        term
        for term in re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", query.lower())
        if len(term) > 3 and term not in stop_words
    }
    scored = []
    for idx, doc in enumerate(docs):
        doc_terms = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", doc.lower()))
        scored.append((len(query_terms & doc_terms), -idx, doc))

    # If query has zero meaningful overlap with any retrieved chunk, it is out of scope.
    if query_terms and max(s[0] for s in scored) == 0:
        return ""

    best_doc = max(scored)[2]
    return best_doc.strip()[:max_chars]


class GenerationService:
    REFUSAL = "I do not have enough information in the provided documentation."
    FALLBACK_MARKER = "Based on the documentation, the most relevant excerpt is:"

    def __init__(self):
        self.client = None

    def initialize(self):
        if self.client is None:
            self.client = ollama.Client(host=settings.OLLAMA_HOST)

    def build_prompt(
        self, question: str, docs: list[str], metas: list[dict], retry: bool = False
    ) -> str:
        context_parts = []
        for doc, meta in zip(docs, metas):
            source = meta.get("source", "unknown")
            chunk_idx = meta.get("chunk_index", 0)
            context_parts.append(f"[{source} (chunk {chunk_idx})]:\n{doc}")

        context_text = "\n\n".join(context_parts)

        retry_instruction = (
            "Copy relevant facts and technical identifiers exactly from the "
            "context. Prefer a short extractive answer when possible.\n"
        ) if retry else ""

        prompt = (
            "You are an expert FastAPI technical documentation assistant.\n"
            "Use ONLY the facts explicitly stated in the Documentation Context below.\n"
            "Answer the specific question directly and concisely in 2-4 sentences.\n"
            "Focus strictly on what is asked; do NOT summarize unrelated topics, query parameter validations, or endpoints from other documents.\n"
            "Do NOT mention user names, company names, testimonials, or case studies.\n"
            "Do NOT write code, imports, decorators, function signatures, or code blocks.\n"
            "Do NOT invent or rename any technical identifiers.\n"
            "If the context does not mention the topic at all, reply ONLY with:\n"
            "'I do not have enough information in the provided documentation.'\n\n"
            f"{retry_instruction}"
            f"Documentation Context:\n{context_text}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        return prompt

    def answer_is_supported(self, answer: str, docs: list[str]) -> bool:
        if answer == self.REFUSAL:
            return True

        context = "\n".join(docs).lower()

        # ── Check 1: known FastAPI API tokens must appear in context ─────────
        api_tokens = re.findall(
            r"@\w+\.\w+|\b(?:FastAPI|APIRouter|Depends|Query|CORSMiddleware|"
            r"BackgroundTasks|JSONResponse|OAuth2PasswordBearer|"
            r"OAuth2PasswordRequestForm)\b",
            answer,
        )
        if any(token.lower() not in context for token in api_tokens):
            return False

        # ── Check 2: Route parameter templates must appear in context ───────
        # Catches invented route syntax like /{param:[^/]+} or /users/:id while ignoring URLs
        clean_for_paths = re.sub(r"https?://[^\s\)]+", "", answer)
        route_patterns = [
            p.rstrip(").,;:'\"")
            for p in re.findall(r"/[\w\-]*\{[^\}\s]+\}|/[\w\-]*:[\w\-]+|/\[\^[^\]]+\]", clean_for_paths)
        ]
        for pattern in route_patterns:
            if pattern.lower() not in context:
                return False

        # ── Check 3: general term-overlap threshold ──────────────────────────
        stop_words = {
            "the", "and", "for", "with", "from", "this", "that", "are", "can", "use", "you",
        }
        answer_terms = {
            term
            for term in re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", answer.lower())
            if len(term) > 3 and term not in stop_words
        }
        context_terms = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_{}@.]*", context))
        overlap = len(answer_terms & context_terms) / max(len(answer_terms), 1)
        return overlap >= 0.25

    def answer_query(self, question: str, top_k: int = 3) -> dict:
        self.initialize()
        docs, metas = retrieval_service.retrieve(question, top_k=top_k)

        raw_answer = ""
        generated = False

        # Two attempts: normal prompt first, then an extractive-nudge retry.
        for retry in (False, True):
            prompt = self.build_prompt(question, docs, metas, retry=retry)
            response = self.client.chat(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0, "num_predict": 220, "repeat_penalty": 1.3},
            )
            raw_answer = response["message"]["content"].strip()
            if self.answer_is_supported(raw_answer, docs):
                generated = raw_answer != self.REFUSAL
                break

        # Both attempts failed grounding → return a verbatim excerpt instead
        # of a bare refusal, matching the notebook's extractive-fallback strategy.
        # If the query is completely out-of-scope (zero overlap), return the clean refusal.
        if not generated:
            excerpt = _select_fallback_excerpt(question, docs)
            if not excerpt:
                raw_answer = self.REFUSAL
            else:
                raw_answer = f"{self.FALLBACK_MARKER}\n\n{excerpt}"

        # Append a verbatim fenced code block from the source when available.
        # Only added for grounded model-generated answers, not for excerpts.
        if generated:
            code_block = next(
                (block for doc in docs for block in extract_code_blocks(doc)),
                None,
            )
            if code_block is not None:
                raw_answer += f"\n\n```python\n{code_block}```"

        sources = sorted(list({meta.get("source", "unknown") for meta in metas}))

        return {
            "answer": raw_answer,
            "sources": sources,
        }


generation_service = GenerationService()
