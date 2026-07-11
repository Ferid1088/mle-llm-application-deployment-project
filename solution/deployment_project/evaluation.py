"""Shared-case evaluation and Markdown report rendering."""

import asyncio
import json

from solution.deployment_project.config import ROOT, Settings
from solution.deployment_project.models import (
    CaseResult,
    EvaluationCase,
    GenerateRequest,
)
from solution.deployment_project.provider import DryProvider
from solution.deployment_project.service import GenerationService, clear_trace_file


def load_cases() -> list[EvaluationCase]:
    path = ROOT / "data" / "evaluation" / "cases.json"
    return [
        EvaluationCase.model_validate(item) for item in json.loads(path.read_text())
    ]


async def evaluate_case(case: EvaluationCase, service: GenerationService) -> CaseResult:
    responses = [
        await service.generate(GenerateRequest(prompt=case.prompt))
        for _ in range(case.repeat)
    ]
    final = responses[-1]
    passed = all(term.lower() in final.text.lower() for term in case.expected_terms)
    return CaseResult(
        case_id=case.case_id,
        passed=passed,
        cache_verified=case.repeat == 1 or final.cache_hit,
        quality_score=final.quality_score,
        latency_ms=final.latency_ms,
    )


def run_evaluation() -> list[CaseResult]:
    settings = Settings(trace_path=ROOT / "solution" / "generated" / "traces.jsonl")
    clear_trace_file(settings.trace_path)
    service = GenerationService(DryProvider(), settings)

    async def run_all() -> list[CaseResult]:
        return [await evaluate_case(case, service) for case in load_cases()]

    return asyncio.run(run_all())


def render_report(results: list[CaseResult]) -> str:
    passed = sum(result.passed and result.cache_verified for result in results)
    rows = "\n".join(
        f"| {result.case_id} | {result.passed} | {result.cache_verified} | "
        f"{result.quality_score:.2f} | {result.latency_ms:.2f} |"
        for result in results
    )
    return f"""# Reference Deployment Evaluation

## Decision

The deterministic reference passes {passed}/{len(results)} functional and cache
checks. It is suitable as a deployment scaffold, not as evidence that a live
provider meets production latency or answer-quality objectives.

## Case Results

| Case | Terms Passed | Cache Verified | Quality | Latency ms |
|---|---:|---:|---:|---:|
{rows}

## Service Health And LLM Signals

- Health and readiness contracts are separate.
- Every request writes cache, generation, usage, release, and quality evidence.
- Dry latency is a smoke metric and must not be treated as live capacity.

## Required Next Experiments

1. Run the same cases against the configured live provider.
2. Run the supplied load profile against the deployed Render URL.
3. Calibrate quality scoring with human-reviewed responses.
"""
