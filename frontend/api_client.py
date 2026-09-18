import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

QUERY_ENDPOINT = "/api/query"


def ask_question(question: str) -> dict:
    base_url = os.getenv("API_BASE_URL")
    if not base_url:
        raise RuntimeError("API_BASE_URL is not configured.")

    response = requests.post(
        f"{base_url.rstrip('/')}{QUERY_ENDPOINT}",
        json={"question": question},
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload.get("answer"), str) or not isinstance(payload.get("sources"), list):
        raise ValueError("The backend returned an invalid response.")
    return payload
