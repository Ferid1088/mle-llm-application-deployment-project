"""Reference dataset and evaluation tests."""

from solution.deployment_project.evaluation import (
    load_cases,
    render_report,
    run_evaluation,
)


def test_case_ids_are_unique() -> None:
    cases = load_cases()
    assert len(cases) == 5
    assert len({case.case_id for case in cases}) == len(cases)


def test_evaluation_covers_every_case() -> None:
    results = run_evaluation()

    assert len(results) == len(load_cases())
    assert all(result.passed for result in results)
    assert all(result.cache_verified for result in results)
    assert "## Decision" in render_report(results)
