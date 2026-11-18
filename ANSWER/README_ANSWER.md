# Northstar LLM Deployment Project: Answer

This folder contains the finished project. It is a standalone copy: run every
command below from inside `ANSWER/`. (The same code also lives in the
repository's top-level `solution/` folder.)

## 1. What the project is

A small **FastAPI service** that answers support questions through an LLM
provider, built so it can be deployed and observed:

- one HTTP endpoint (`POST /generate`) plus health and readiness checks,
- an in-memory **cache** so identical requests are not sent to the provider twice,
- **bounded concurrency and timeouts** around the provider call,
- **traces** for every request, written to a JSONL file or to **Langfuse**,
- a **Docker image** that runs the same service locally and on **Render** (Free plan),
- an **evaluation** of five shared cases and a **load test**,
- a small **chat web page** at `/` to try it from a browser.

Current deployment uses the **dry provider**: a stand-in that returns canned text,
so no API key or quota is needed. It only answers four exact phrases
(`duplicate-payment`, `locked account`, `delete all personal`, `active incident`);
everything else returns "I cannot confirm this from approved policy." Real answers
need `MODEL_PROVIDER=groq` (or another provider) and an API key.

## 2. How a request flows

```text
Browser / curl
     |  POST /generate {prompt, max_tokens, temperature}
     v
app.py (FastAPI)  --validates-->  models.py (GenerateRequest)
     v
service.py (GenerationService.generate)
     |-- build cache key (model + temperature + max_tokens + prompt, SHA-256)
     |-- cache hit?  yes -> reuse stored answer, no provider call, 0 new tokens
     |               no  -> wait for a concurrency slot, call provider with timeout,
     |                      store result in cache (TTL 300 s, max 1024 entries)
     |-- compute quality score (keyword heuristic)
     |-- record a trace (never blocks or fails the answer)
     v
GenerateResponse {text, model, usage, cache_hit, latency_ms, quality_score, trace_id}
```

Errors: an invalid or blank prompt gets **422** before any provider call. A
provider timeout gets **504**. Any other provider failure gets **502** with a
generic message (no internal details leak). A failed request is still traced
with status `error`.

## 3. Every file explained

### Application: `solution/deployment_project/`

| File | What it does |
|---|---|
| `app.py` | Creates the FastAPI app. Routes: `GET /` (chat page), `GET /health` (always 200 if the process runs), `GET /ready` (shows provider and model, no provider call), `POST /generate`. Maps errors to 504/502 and flushes Langfuse on shutdown. |
| `config.py` | `Settings` dataclass read from environment variables: provider, model, cache TTL, max concurrency, timeout, trace sink and path, Langfuse environment and release. Validates values (positive concurrency, finite timeout). |
| `models.py` | Pydantic contracts: `GenerateRequest` (prompt 1 to 8000 chars, max_tokens 1 to 2048, temperature 0 to 2), `GenerateResponse`, `Usage`, `ProviderResult`, `TraceRecord`, `EvaluationCase`, `CaseResult`. |
| `provider.py` | `DryProvider` (offline, canned answers) and `ChatProvider` (LangChain wrapper for Groq, Mistral, OpenRouter, Google, OpenAI). `build_provider()` picks one from `MODEL_PROVIDER`. |
| `service.py` | `GenerationService`: cache, timeout, concurrency semaphore, quality score, trace recording. The core logic of the project. |
| `tracing.py` | Two trace sinks. `JsonlTraceSink` appends one JSON line per request. `LangfuseTraceSink` sends a root span, an `llm-generation` observation (cache misses only) with token usage, and a `quality` score. `build_trace_sink()` chooses by `TRACE_SINK`. |
| `evaluation.py` | Loads `data/evaluation/cases.json`, runs each case against the service, checks expected terms and cache behavior, renders a Markdown report. |
| `cli.py`, `__main__.py` | Command line: `inspect-data` prints case and load-profile counts; `evaluate` runs the cases and writes `reports/generated/evaluation.md`. |
| `static/index.html` | The chat page. Calls `/generate` and shows cache hit or miss, latency, tokens, model, quality and trace ID. Works in light and dark mode. |
| `__init__.py` | Marks the folder as a package. |

### Deployment files: `solution/`

| File | What it does |
|---|---|
| `Dockerfile` | Python 3.13 slim image, installs locked dependencies with `uv sync --locked`, runs as a non-root user, serves on port 8000 with uvicorn. |
| `render.yaml` | Reference Blueprint documenting the Render settings (Free Docker web service, env vars, `/health` check). Not used to deploy: the Blueprint flow asks for a payment method, so the service was created with **New > Web Service**. |
| `README.md` | The reference solution's own notes. |
| `reports/reference_evaluation.md` | The reference evaluation result that shipped with the exercise. |

### Tests: `solution/tests/`

| File | What it covers |
|---|---|
| `test_api.py` | Health and generation contract, blank prompt rejected, provider errors do not leak details, OpenAI timeout returns 504. |
| `test_service.py` | A repeated request hits the cache and writes a complete trace. |
| `test_provider.py` | Groq is the default provider and needs its key, environment selects the matching provider and model, async generation preserves usage and limits, unusable answers are rejected, no retry or invented answer. |
| `test_tracing.py` | The Langfuse export contract (cache hit or miss, status, quality). |
| `test_evaluation.py` | Case IDs are unique, every case is evaluated, a real miss-then-hit cache transition is required, expected terms match whole words only. |
| `test_boundaries.py` | Blank prompts rejected, invalid configuration fails early, the timeout covers provider and queue time, empty provider results are not cached, cache expiry and disabled cache, telemetry failure does not break an answer, a failed provider is traced without leaking exception text. |

`conftest.py` (project root) forces tests to run offline: dry provider, JSONL
tracing, Langfuse disabled, and a fresh cache and trace file per test. No API
keys are needed.

### Data, scripts, config

| File | What it does |
|---|---|
| `data/evaluation/cases.json` | The five shared evaluation cases (refund_supported, account_access, privacy_handoff, incident_status, unsupported_policy). Labels must not be edited. |
| `data/operations/load_profile.json` | Load profile: 40 requests, 5 in flight, and the objectives (p95 at most 2000 ms, error rate at most 2%, mean quality at least 0.8). |
| `scripts/load_test.py` | Async load probe. Sends N requests with C in flight to `POST /generate`, prints throughput, mean and p95 latency, and error rate. |
| `pyproject.toml`, `uv.lock` | Python 3.13 project definition and the locked dependency versions. |
| `.env.example` | Template of all environment variables. Copy to `.env` and fill in keys. **Never commit real keys.** |
| `reports/deployment_report.md` | The final report: architecture, results, objectives, recommendation. |
| `reports/evaluation.md` | Generated output of the five-case evaluation. |

## 4. Environment variables

| Variable | Meaning | Value used on Render |
|---|---|---|
| `MODEL_PROVIDER` | `dry`, `groq`, `mistral`, `openrouter`, `google`, `openai` | `dry` |
| `GROQ_API_KEY`, `GROQ_MODEL` | Needed only when the provider is `groq` | not set |
| `CACHE_TTL_SECONDS` | Cache lifetime | 300 (default) |
| `MAX_CONCURRENT_REQUESTS` | Simultaneous provider calls | 4 (default) |
| `REQUEST_TIMEOUT_SECONDS` | Provider timeout | 30 (default) |
| `TRACE_SINK` | `jsonl` (file) or `langfuse` | `langfuse` |
| `TRACE_PATH` | JSONL file location | default |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` | Langfuse API keys (secret) | set in Render only |
| `LANGFUSE_BASE_URL` | Langfuse region | `https://cloud.langfuse.com` |
| `LANGFUSE_TRACING_ENVIRONMENT` | Environment label in traces | `production` |
| `LANGFUSE_RELEASE` | Release label in traces | `v1` |

## 5. Run it: terminal guide

Prerequisites: **Git**, **uv** (https://docs.astral.sh/uv/), and **Docker Desktop**
(installed and running).

### 5.1 Get the code and install

```bash
git clone https://github.com/Ferid1088/mle-llm-application-deployment-project.git
cd mle-llm-application-deployment-project/ANSWER
uv sync
```

### 5.2 Run the tests (no keys needed)

```bash
uv run pytest -q
```

Expected: `79 passed`.

### 5.3 Run the service locally (without Docker)

```bash
MODEL_PROVIDER=dry TRACE_SINK=jsonl \
  uv run uvicorn solution.deployment_project.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the chat page. In a second terminal:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
for i in 1 2; do
  curl -s -X POST http://127.0.0.1:8000/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt":"What evidence is required for a duplicate-payment refund?"}'
  echo
done
```

The first response has `"cache_hit":false`, the second `"cache_hit":true`.

### 5.4 Evaluation and load test

```bash
uv run python -m solution.deployment_project inspect-data
MODEL_PROVIDER=dry uv run python -m solution.deployment_project evaluate
uv run python scripts/load_test.py --url http://127.0.0.1:8000 --requests 40 --concurrency 5
```

`evaluate` writes `reports/generated/evaluation.md`. Run the load test while the
service from 5.3 (or from 5.5) is running. Use the Render URL instead of
`127.0.0.1:8000` to test the hosted service.

### 5.5 Run with Docker

Start Docker Desktop first, then, still inside `ANSWER/`:

```bash
docker build -f solution/Dockerfile -t llm-deploy:local .
docker run -d --name llm-deploy -p 8000:8000 \
  -e MODEL_PROVIDER=dry -e TRACE_SINK=jsonl \
  llm-deploy:local
curl -s http://127.0.0.1:8000/health
docker logs llm-deploy
```

Open http://localhost:8000. To see the JSONL traces inside the container:

```bash
docker exec llm-deploy tail -n 2 solution/generated/traces.jsonl
```

Stop and remove it:

```bash
docker rm -f llm-deploy
```

### 5.6 Optional: send traces to Langfuse from your machine

```bash
cp .env.example .env     # then edit .env and set the Langfuse keys
docker run -d --name llm-deploy -p 8000:8000 --env-file .env \
  -e MODEL_PROVIDER=dry -e TRACE_SINK=langfuse llm-deploy:local
```

Keep `.env` out of git (it is already in `.gitignore`).

### 5.7 Optional: real answers with a live provider

Set in `.env` (or in Render's Environment): `MODEL_PROVIDER=groq`,
`GROQ_API_KEY=<your key>`, `GROQ_MODEL=openai/gpt-oss-20b`. The Render URL is
public, so share it only while it runs the dry provider.

## 6. Links

| What | Link |
|---|---|
| Live service and chat page (Render) | https://mle-llm-application-deployment-project-xerl.onrender.com |
| API docs (try `POST /generate`) | https://mle-llm-application-deployment-project-xerl.onrender.com/docs |
| Health check | https://mle-llm-application-deployment-project-xerl.onrender.com/health |
| Readiness (shows provider and model) | https://mle-llm-application-deployment-project-xerl.onrender.com/ready |
| Render dashboard (services, deploys, logs, environment) | https://dashboard.render.com |
| Langfuse Cloud (EU) | https://cloud.langfuse.com |
| Langfuse project, Tracing page | https://cloud.langfuse.com/project/cmwlt6mrn03fdad0e9js52qs6/traces |
| GitHub repository | https://github.com/Ferid1088/mle-llm-application-deployment-project |
| Get a Groq API key | https://console.groq.com/keys |

On the Render dashboard, open your service, then **Deploys**, **Logs**,
**Environment** or **Settings** in the left menu. In Langfuse, open **Tracing**
in the left menu and set the time range to cover your requests. Search a
`trace_id` from the API response to find a specific request. The Langfuse
project link is copied from a browser address bar; if it does not open, use the
Cloud link and pick your project.

The Free Render instance sleeps when idle: the first request after a pause can take about 50 seconds.

## 7. Results and status

- Local: 79 tests pass; 5/5 evaluation cases pass; load run 40/40 successes.
- Render (dry): 40/40 successes, p95 230.83 ms, 0% errors.
- Langfuse: traces arrive with environment `production`, release tag `v1`, and
  `llm-generation` observations on cache misses only.
- Recommendation in `reports/deployment_report.md`: **revise**. Nothing was
  measured with a live provider, so answer quality and cost are unmeasured.
- Known gaps: the `cache-lookup` stage is in the JSONL trace but not a nested
  Langfuse observation, cost is not exported, no failure trace was captured, and
  the Langfuse dashboard (bonus) was not built.
