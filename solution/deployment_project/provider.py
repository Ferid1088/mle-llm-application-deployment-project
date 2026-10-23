"""Deterministic and optional Groq providers."""

from typing import Protocol

from openai import AsyncOpenAI

from solution.deployment_project.config import Settings
from solution.deployment_project.models import GenerateRequest, ProviderResult, Usage


class Provider(Protocol):
    async def generate(self, request: GenerateRequest) -> ProviderResult: ...


class DryProvider:
    """Produce stable policy-shaped answers for the shared cases."""

    model = "dry-northstar-v1"

    async def generate(self, request: GenerateRequest) -> ProviderResult:
        prompt = request.prompt.lower()
        if "duplicate-payment" in prompt:
            text = "Collect the receipt and transaction identifier before review."
        elif "locked account" in prompt:
            text = "Verify identity, then issue the approved reset flow."
        elif "delete all personal" in prompt:
            text = "Route the privacy request to human review."
        elif "active incident" in prompt:
            text = "Share only confirmed updates from the status page."
        else:
            text = "I cannot confirm this from approved policy."
        return ProviderResult(
            text=text,
            model=self.model,
            usage=Usage(
                input_tokens=len(request.prompt.split()),
                output_tokens=len(text.split()),
            ),
        )


class GroqProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.api_key:
            raise ValueError("GROQ_API_KEY is required for live mode")
        self.model = settings.model
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=settings.request_timeout_seconds,
            max_retries=0,
        )

    async def generate(self, request: GenerateRequest) -> ProviderResult:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": request.prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        if (
            not response.choices
            or not (response.choices[0].message.content or "").strip()
        ):
            raise ValueError("Provider returned no answer")
        usage = response.usage
        return ProviderResult(
            text=response.choices[0].message.content or "",
            model=self.model,
            usage=Usage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            ),
        )


def build_provider(settings: Settings) -> Provider:
    if settings.provider == "dry":
        return DryProvider()
    if settings.provider == "groq":
        return GroqProvider(settings)
    raise ValueError(f"Unsupported provider: {settings.provider}")
