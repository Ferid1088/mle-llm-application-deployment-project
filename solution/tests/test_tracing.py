"""Cloud exports preserve privacy and distinguish cache hits from generation."""

from contextlib import contextmanager, nullcontext

import pytest

from solution.deployment_project.models import TraceRecord, Usage
from solution.deployment_project.tracing import LangfuseTraceSink


@pytest.mark.parametrize("cache_hit", [False, True])
def test_cloud_export_contract(monkeypatch, cache_hit):
    calls = []

    class Observation:
        active = True

        def update(self, **values):
            assert self.active
            calls.append(values)

        def score(self, **values):
            assert self.active
            calls.append(values)

    class Client:
        @contextmanager
        def start_as_current_observation(self, **values):
            calls.append(values)
            observation = Observation()
            yield observation
            observation.active = False

    monkeypatch.setattr(
        "solution.deployment_project.tracing.get_client", lambda: Client()
    )
    monkeypatch.setattr(
        "solution.deployment_project.tracing.propagate_attributes",
        lambda **kwargs: nullcontext(),
    )
    trace = TraceRecord(
        trace_id="test",
        model="test",
        prompt="private customer question",
        output="private customer answer",
        latency_ms=123,
        cache_hit=cache_hit,
        usage=Usage(input_tokens=0, output_tokens=0),
        quality_score=0.9,
    )
    LangfuseTraceSink().record(trace)
    assert trace.prompt not in repr(calls)
    assert trace.output not in repr(calls)
    generations = [call for call in calls if call.get("as_type") == "generation"]
    assert len(generations) == (0 if cache_hit else 1)
    assert calls[0]["metadata"]["request_latency_ms"] == 123
