# Reference Deployment Evaluation

## Decision

The deterministic reference passes 5/5 functional and cache
checks. It is suitable as a deployment scaffold, not as evidence that a live
provider meets production latency or answer-quality objectives.

## Case Results

| Case | Terms Passed | Cache Verified | Quality | Latency ms |
|---|---:|---:|---:|---:|
| refund_supported | True | True | 0.90 | 0.00 |
| account_access | True | True | 0.90 | 0.01 |
| privacy_handoff | True | True | 0.90 | 0.01 |
| incident_status | True | True | 0.90 | 0.01 |
| unsupported_policy | True | True | 0.90 | 0.00 |

## Service Health And LLM Signals

- Health and readiness contracts are separate.
- Every request writes cache, generation, usage, release, and quality evidence.
- Dry latency is a smoke metric and must not be treated as live capacity.

## Required Next Experiments

1. Run the same cases against the configured live provider.
2. Run the supplied load profile against the deployed Render URL.
3. Calibrate quality scoring with human-reviewed responses.
