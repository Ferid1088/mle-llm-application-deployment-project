# Deployment Report

Date: 2026-11-18 · Revision: `5163cc2` (branch `main`)

## Recommendation

**Revise. Do not approve for production yet.**

The deployment path is verified end to end with the **dry** provider: the same
container runs locally and on a Free Render web service, caching works, and
traces reach Langfuse. No live provider was ever called, so answer quality,
cost and live latency are **unmeasured**. The three changes listed at the end
would move this to "deploy".

Deciding evidence: hosted dry load run (40/40 successes, p95 230.83 ms), the
cache miss/hit trace pair in Langfuse (`2e05b569b61d52e062753e29` /
`a60b10e65ea10261299a5406`), and the next experiment: run the five cases and the
load profile with a live provider and score the answers.

## Deployment Architecture And Configuration

| Item | Value |
|---|---|
| Service URL | https://mle-llm-application-deployment-project-xerl.onrender.com |
| Platform | Render Web Service, Free instance, Docker runtime |
| Dockerfile | `solution/Dockerfile` (Python 3.13 slim, `uv sync --locked`, non-root user) |
| Instances | 1 (Free tier; no autoscaling) |
| Provider / model | `dry` / `dry-northstar-v1` |
| Tracing | `TRACE_SINK=langfuse`, Langfuse Cloud EU (`https://cloud.langfuse.com`) |
| Environment / release | `production` / `v1` |
| Health check | `/health` |
| Cache | process-local, TTL 300 s |
| UI | chat page at `/`; API docs at `/docs` |

Secrets (Langfuse keys) are set in Render's environment, not in the repo or
image. A real Groq key had been committed in `.env.example`; it was removed
and the unpushed commit was amended, so it never reached GitHub (history scan
found no `gsk_` strings). The key should still be rotated because it sat in a
tracked file.

Free-tier limits: the instance spins down when idle (cold start of about 50 s)
and has one process-local cache, so a restart or second instance would start
with a cold cache. One instance is the right choice for a dry demo; it is not
a scaling strategy for production.

## Functional Results (dry, local)

Command: `uv run python -m solution.deployment_project evaluate`

| Case | Terms matched | Cache verified | Mean score |
|---|---|---|---:|
| refund_supported | yes | yes | 0.90 |
| account_access | yes | n/a | 0.90 |
| privacy_handoff | yes | n/a | 0.90 |
| incident_status | yes | n/a | 0.90 |
| unsupported_policy | yes | n/a | 0.90 |

All 5/5 cases pass. The dry provider returns a fixed refusal, so this checks
the plumbing, not answer correctness. Mean latency for `refund_supported`
(59.65 ms) includes first-call warm-up. The test suite passes (79 tests) without API keys.

Cache evidence: the first identical request returned `cache_hit: false` and
the repeat `cache_hit: true`, locally, in the container and on Render. The hit
has 0 provider tokens and no generation span in its trace.

## Load Results

Command: `uv run python scripts/load_test.py --url <URL> --requests 40 --concurrency 5`.
Workload: 40 HTTP attempts, 5 in flight, three cycled prompts (cache-heavy).
All runs use the dry provider.

| Run | Cache at start | Throughput (rps) | Mean ms | p95 ms | Errors |
|---|---|---:|---:|---:|---:|
| Local container | cold (restarted) | 293.97 | 10.09 | 44.63 | 0/40 (0.00%) |
| Local container | warm | 376.37 | 7.66 | 10.66 | 0/40 (0.00%) |
| Render (Free) | warm (earlier traffic) | 40.25 | 115.82 | 230.83 | 0/40 (0.00%) |

p95 is computed by the probe over all attempts. There were no failures, so
including or excluding them gives the same number. Render latency is network
round trip from this machine, not compute. These numbers show nothing about a live provider.

## Objectives

| Objective | Target | Result | Status |
|---|---|---|---|
| p95 latency | ≤ 2,000 ms | 230.83 ms (hosted, dry) | Pass for the dry workload only |
| Error rate | ≤ 2% | 0.00% (0/40, hosted, dry) | Pass for the dry workload only |
| Mean quality | ≥ 0.8 | 0.90 keyword heuristic, 5 cases | **Not measured**: the dry provider returns a fixed refusal and the heuristic does not check correctness |

## Traces And Observability

Verified in Langfuse (EU project) after sending a synthetic miss, hit and a
different prompt to Render: 3 root observations (`northstar-support-request`)
and 2 `llm-generation` observations (the two misses; the hit has none). Each has
environment `production`, tags `deployment-project` and `v1`, and model
`dry-northstar-v1`. Inputs and outputs are stored only as `prompt_chars` and
`output_chars`, so raw prompt text is not exported.

Known gaps against the project brief:

- The exporter sends only the root span plus an `llm-generation` observation
  (misses only). The `cache-lookup` stage is recorded in the JSONL trace `spans`
  field but is **not** a nested Langfuse observation. Cache evidence in Langfuse
  is the `cache_hit` metadata and the absent generation on hits.
- The quality score is exported as a Langfuse score named `quality` (not yet
  confirmed in the Scores page of the UI).
- Cost is empty: the exporter sends token usage but no cost, and the dry
  provider has no pricing.

## Failure Analysis

No failing request was captured as a Langfuse trace. Failure behavior is
covered by unit tests only: a blank prompt is rejected with 422 before the
provider is called (confirmed against the local container), provider errors
return 502 without leaking details, and timeouts return 504. A real failure
trace remains to be produced, for example with an invalid provider key.

## Masking And Retention

Raw prompts and outputs are not exported (character counts only). Before using
a live provider with customer text, decide on retention for the trace metadata
and keep sampling at 100% only while volume is low.

## Three Prioritized Changes Before Production Approval

1. **Run a live provider evaluation.** Set a provider key in Render only,
   rerun the five cases and the load profile, and record real latency, tokens, cost and
   errors. This replaces every "dry only" caveat above.
2. **Replace the keyword quality score** with human-reviewed answers, and
   record it as a Langfuse score so the dashboard widget is meaningful.
3. **Capture a failure trace and add auth/rate limiting.** The URL is public,
   so anyone can use the provider quota. Also move off the single Free instance
   (or use a shared cache) before any traffic that matters.
