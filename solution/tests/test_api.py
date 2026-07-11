"""Reference API tests."""

import asyncio

from httpx import ASGITransport, AsyncClient

from solution.deployment_project.app import app, service


async def request(method: str, path: str, payload: dict[str, object] | None = None):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.request(method, path, json=payload)


def test_health_and_generation_contract() -> None:
    health = asyncio.run(request("GET", "/health"))
    assert health.status_code == 200
    readiness = asyncio.run(request("GET", "/ready"))
    assert readiness.json()["model"] == "openai/gpt-oss-20b"
    response = asyncio.run(request("POST", "/generate", {"prompt": "locked account"}))
    assert response.status_code == 200
    assert "identity" in response.json()["text"].lower()


def test_invalid_prompt_is_rejected() -> None:
    assert asyncio.run(request("POST", "/generate", {"prompt": ""})).status_code == 422


def test_provider_errors_do_not_leak_details(monkeypatch) -> None:
    class FailingProvider:
        async def generate(self, request):
            raise RuntimeError("secret provider response")

    monkeypatch.setattr(service, "provider", FailingProvider())
    response = asyncio.run(request("POST", "/generate", {"prompt": "error-path-check"}))

    assert response.status_code == 502
    assert response.json()["detail"] == "Generation provider unavailable"
