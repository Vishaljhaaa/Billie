# Dynamic Knowledge Base Chatbot

## Problem Statement

This project builds a chatbot that can continuously expand its knowledge base instead of staying frozen after deployment. The goal is to ingest new information from trusted sources, update a vector database incrementally, and let the chatbot answer with the freshest available context.

As an internship-style extension on the same training project, this repository now also includes reproducible retrieval experiments, baseline-vs-improved model comparisons, benchmark data, and saved visual outputs.

## Dataset

The project uses the same chatbot domain and extends it with a small local knowledge corpus for reproducible experiments:

- [knowledge/company_handbook.txt](C:/Users/vishal/Desktop/ASS1/knowledge/company_handbook.txt)
- [knowledge/product_updates.txt](C:/Users/vishal/Desktop/ASS1/knowledge/product_updates.txt)
- [knowledge/security_playbook.txt](C:/Users/vishal/Desktop/ASS1/knowledge/security_playbook.txt)

Benchmark questions and expected evidence are stored in:

- [experiments/benchmark_dataset.json](C:/Users/vishal/Desktop/ASS1/experiments/benchmark_dataset.json)

This keeps the internship work on the same chatbot project rather than switching to a new dataset or unrelated system.

## Methodology

### Core system

- Source ingestion from local files and web pages
- Fingerprint-based change detection so only changed sources are re-indexed
- Chunk-based retrieval store with persistent storage
- Scheduled background sync plus manual admin-triggered sync
- Optional LLM answer generation with retrieval fallback
- API key protection, metrics, and admin dashboard

### Preprocessing and feature engineering

- HTML cleanup removes scripts, styles, and non-content tags before indexing
- Documents are normalized and chunked with configurable chunk size and overlap
- Each chunk becomes a searchable retrieval unit with source metadata
- Source fingerprints are stored in SQLite for incremental refresh logic

### Model comparison

The experiment layer compares two retrieval strategies on the same chatbot knowledge base:

1. `KeywordOverlap` baseline
   Scores chunks by raw token overlap with the user question.
2. `CosineOverlap` improved model
   Scores chunks with cosine similarity over token-frequency vectors and uses chunk overlap for better context retention.

This gives a lightweight but reproducible comparison between a simpler baseline and a stronger retrieval setup on the same project.

## Repository Structure

- [app/main.py](C:/Users/vishal/Desktop/ASS1/app/main.py): FastAPI entrypoint and dependency wiring
- [app/updater.py](C:/Users/vishal/Desktop/ASS1/app/updater.py): incremental knowledge base refresh logic
- [app/vector_store.py](C:/Users/vishal/Desktop/ASS1/app/vector_store.py): Chroma integration plus local fallback backend
- [app/chatbot.py](C:/Users/vishal/Desktop/ASS1/app/chatbot.py): retrieval and LLM-backed response flow
- [app/sources.py](C:/Users/vishal/Desktop/ASS1/app/sources.py): source loading, preprocessing, retry/backoff
- [app/monitoring.py](C:/Users/vishal/Desktop/ASS1/app/monitoring.py): Prometheus metrics
- [experiments/run_benchmark.py](C:/Users/vishal/Desktop/ASS1/experiments/run_benchmark.py): benchmark runner
- [tests](C:/Users/vishal/Desktop/ASS1/tests): unit and integration tests

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:create_app --factory --reload
```

Optional dense-vector backend:

```bash
pip install -r requirements-chroma.txt
```

## Configuration

The knowledge sources are configured in [sources.json](C:/Users/vishal/Desktop/ASS1/sources.json).

Important environment variables:

- `CHATBOT_API_KEY`: protects `/chat`
- `CHATBOT_ADMIN_API_KEY`: protects `/sync` and `/admin/*`
- `OPENAI_API_KEY`: enables LLM-backed responses
- `OPENAI_MODEL`: defaults to `gpt-4o-mini`
- `VECTOR_STORE_BACKEND`: set `local` to force the built-in fallback backend
- `SOURCE_MAX_RETRIES`, `SOURCE_TIMEOUT_SECONDS`, `SOURCE_RETRY_BACKOFF_SECONDS`: ingestion resilience controls

## Experiments and Results

Run the benchmark:

```bash
python experiments/run_benchmark.py
```

This generates:

- [artifacts/benchmark_results.json](C:/Users/vishal/Desktop/ASS1/artifacts/benchmark_results.json)
- [artifacts/retriever_top1_accuracy.png](C:/Users/vishal/Desktop/ASS1/artifacts/retriever_top1_accuracy.png)
- [artifacts/retriever_keyword_recall.png](C:/Users/vishal/Desktop/ASS1/artifacts/retriever_keyword_recall.png)

Metrics reported:

- `top1_accuracy`
- `top3_accuracy`
- `avg_keyword_recall`

Current benchmark results from the checked-in experiment run:

| Model | Top-1 Accuracy | Top-3 Accuracy | Avg Keyword Recall |
|---|---:|---:|---:|
| KeywordOverlap | 1.00 | 1.00 | 0.80 |
| CosineOverlap | 1.00 | 1.00 | 0.733 |

Insight:

- Both models retrieve the correct source on every benchmark question.
- The keyword baseline retains slightly higher keyword recall on this small dataset.
- This suggests the current benchmark corpus is easy for source-level retrieval and that future work should include harder paraphrased questions or a denser semantic retriever for clearer separation.

## API Usage

### How to use the chatbot

1. Start the server:

```bash
python -m uvicorn app.main:create_app --factory --reload
```

2. Open these URLs in your browser:

- Home page: `http://127.0.0.1:8000/`
- Admin dashboard: `http://127.0.0.1:8000/admin`
- Health check: `http://127.0.0.1:8000/health`
- Metrics: `http://127.0.0.1:8000/metrics`

3. Send a `POST` request to `/chat` with your question and `X-API-Key`.

PowerShell example:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://127.0.0.1:8000/chat `
  -Headers @{ "X-API-Key" = "chat-secret-123" } `
  -ContentType "application/json" `
  -Body '{"question":"How does the chatbot update its knowledge base?"}'
```

Example response:

```json
{
  "answer": "The chatbot updates its knowledge base by re-checking configured sources, detecting changes, and re-indexing only changed content.",
  "sources": [
    "C:\\Users\\vishal\\Desktop\\ASS1\\knowledge\\company_handbook.txt"
  ],
  "used_llm": false
}
```

4. To refresh the knowledge base manually, send a `POST` request to `/sync` with `X-Admin-Key`.

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://127.0.0.1:8000/sync `
  -Headers @{ "X-Admin-Key" = "admin-secret-123" }
```

5. To use the admin dashboard, open `/admin`, enter the admin key, then use:

- `Load Status` to inspect indexed sources and sync metrics
- `Run Sync` to trigger an immediate update

Trigger a manual refresh:

```bash
curl -X POST http://127.0.0.1:8000/sync -H "X-Admin-Key: replace-with-admin-key"
```

Ask a question:

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: replace-with-chat-key" ^
  -d "{\"question\":\"How does the chatbot learn new information?\"}"
```

Open the admin dashboard:

```bash
start http://127.0.0.1:8000/admin
```

### Full API reference

#### `GET /`

Purpose:
- Shows the landing page for the project

Auth:
- none

Typical use:
- Open `http://127.0.0.1:8000/` in a browser

#### `GET /health`

Purpose:
- Returns a simple health status for the running service

Auth:
- none

Example response:

```json
{
  "status": "ok"
}
```

#### `GET /metrics`

Purpose:
- Exposes Prometheus-style runtime metrics

Auth:
- none

Typical use:
- Monitoring request counts, sync runs, and LLM usage

#### `POST /chat`

Purpose:
- Accepts a user question and returns an answer based on the indexed knowledge base

Auth:
- requires `X-API-Key` when `CHATBOT_API_KEY` is configured

Request body:

```json
{
  "question": "How does the chatbot update its knowledge base?"
}
```

Response fields:

- `answer`: final chatbot response
- `sources`: source locations used during retrieval
- `used_llm`: whether the response came through the LLM layer

#### `POST /sync`

Purpose:
- Triggers an immediate knowledge-base refresh

Auth:
- requires `X-Admin-Key` when `CHATBOT_ADMIN_API_KEY` is configured

Response fields:

- `updated_sources`: sources re-indexed in this run
- `skipped_sources`: unchanged sources skipped by fingerprint comparison
- `failed_sources`: sources that failed to update
- `error_details`: per-source failure messages when applicable

#### `GET /admin`

Purpose:
- Opens the browser-based admin dashboard

Auth:
- the page itself is open, but dashboard actions use the admin key

#### `GET /admin/status`

Purpose:
- Returns the current admin status view as JSON

Auth:
- requires `X-Admin-Key` when configured

Response fields:

- `last_sync_at`
- `source_count`
- `indexed_sources`
- `last_sync_summary`
- `metrics`

#### `POST /admin/sync`

Purpose:
- Triggers a manual sync from the admin workflow

Auth:
- requires `X-Admin-Key` when configured

Returns:
- the same sync payload as `POST /sync`

## Code Flow

### End-to-end request flow

1. The app starts in [app/main.py](C:/Users/vishal/Desktop/ASS1/app/main.py) through `create_app()`.
2. `create_app()` builds shared services such as the vector store, updater, chatbot, auth manager, scheduler, and monitoring layer.
3. On startup, the FastAPI lifespan hook runs one sync immediately so the knowledge base is available before the first chat request.
4. The scheduler in [app/scheduler.py](C:/Users/vishal/Desktop/ASS1/app/scheduler.py) keeps refreshing sources in the background at the configured interval.
5. When a user calls `/chat`, the auth layer checks `X-API-Key`, then the chatbot service retrieves the most relevant chunks from the vector store.
6. If an LLM is configured, those retrieved chunks are passed into the LLM prompt to produce the final answer.
7. If the LLM is unavailable or not configured, the app falls back to a retrieval-only answer.
8. Monitoring counters and request latency metrics are updated throughout the request lifecycle.

### Knowledge ingestion flow

1. Source definitions are read from [sources.json](C:/Users/vishal/Desktop/ASS1/sources.json) through [app/config.py](C:/Users/vishal/Desktop/ASS1/app/config.py).
2. The updater in [app/updater.py](C:/Users/vishal/Desktop/ASS1/app/updater.py) loops through each configured source.
3. [app/sources.py](C:/Users/vishal/Desktop/ASS1/app/sources.py) loads content from local files or URLs.
4. URL content is cleaned with BeautifulSoup so only useful text is indexed.
5. Each source is fingerprinted, and [app/state.py](C:/Users/vishal/Desktop/ASS1/app/state.py) compares it to the last stored fingerprint in SQLite.
6. If the source is unchanged, it is skipped.
7. If the source changed, [app/text_utils.py](C:/Users/vishal/Desktop/ASS1/app/text_utils.py) splits it into chunks.
8. [app/vector_store.py](C:/Users/vishal/Desktop/ASS1/app/vector_store.py) replaces only that source’s existing chunks in the retrieval store.
9. The new fingerprint and timestamp are stored so the next sync can be incremental again.

### Retrieval and answer generation flow

1. A chat question reaches [app/chatbot.py](C:/Users/vishal/Desktop/ASS1/app/chatbot.py).
2. The chatbot asks the vector store for the top `k` matching chunks.
3. The vector store uses either:
- Chroma embeddings when the optional Chroma backend is available
- a local persistent cosine/keyword-style fallback backend otherwise
4. Matching chunks are converted into source-backed context snippets.
5. [app/llm.py](C:/Users/vishal/Desktop/ASS1/app/llm.py) formats a retrieval-augmented prompt for an OpenAI-compatible API when `OPENAI_API_KEY` is present.
6. If the LLM call succeeds, the API returns an LLM-backed answer with `used_llm: true`.
7. If the LLM call fails, the chatbot returns a retrieval-only fallback answer with `used_llm: false`.

### Supporting components

- [app/auth.py](C:/Users/vishal/Desktop/ASS1/app/auth.py) enforces API-key protection for chat and admin routes
- [app/monitoring.py](C:/Users/vishal/Desktop/ASS1/app/monitoring.py) records counters, latency, sync stats, and LLM call metrics
- [app/admin.py](C:/Users/vishal/Desktop/ASS1/app/admin.py) renders the landing page and admin dashboard UI
- [experiments/run_benchmark.py](C:/Users/vishal/Desktop/ASS1/experiments/run_benchmark.py) evaluates retriever behavior on the same project knowledge base

## Testing and Reproducibility

Run all automated tests:

```bash
python -m pytest
```

What is covered:

- API auth and admin endpoints
- Retrieval and LLM fallback behavior
- Source-loader retry logic
- Benchmark artifact generation

## Visual Outputs

The benchmark script saves comparison plots for the retrieval models so the repo includes presentation-ready outputs rather than only code:

- accuracy comparison bar chart
- keyword recall comparison bar chart

## Notes for GitHub Submission

This repository is now structured to be uploaded directly to GitHub with:

- a clear problem statement
- documented dataset and preprocessing
- methodology and model comparison
- reproducible commands
- automated tests
- generated metrics and plots

The one thing not done from inside this environment is the actual GitHub push. Once you want, I can also help you prepare a final `git` commit flow or a polished project description for the repo page.
