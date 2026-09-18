import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.generation import GenerationService
from app.services import generation as generation_module

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data

def test_query_success_happy_path(client):
    payload = {"question": "How do I handle CORS in FastAPI?"}
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) > 0

def test_query_invalid_input_empty_payload(client):
    response = client.post("/query", json={})
    assert response.status_code == 422

def test_query_invalid_input_short_question(client):
    response = client.post("/query", json={"question": "a"})
    assert response.status_code == 422

def test_api_v1_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_grounding_guard_uses_excerpt_fallback(monkeypatch):
    service = GenerationService()
    service.client = type(
        "FakeClient",
        (),
        {"chat": lambda self, **kwargs: {"message": {"content": "@app.path('/fake')"}}},
    )()
    monkeypatch.setattr(
        generation_module.retrieval_service,
        "retrieve",
        lambda question, top_k=3: (
            ["Use @app.get('/items/{item_id}') for a path parameter."],
            [{"source": "tutorial_path-params.md", "chunk_index": 0}],
        ),
    )

    result = service.answer_query("How do I define a path parameter?")

    assert "@app.path" not in result["answer"]
    assert "most relevant excerpt" in result["answer"]
    assert result["sources"] == ["tutorial_path-params.md"]
