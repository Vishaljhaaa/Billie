# Billie Baseline Report

**Run date:** 2026-09-26  
**Purpose:** Reproducible Milestone 1 baseline. This report does not claim model-quality improvements.

## Environment

- OS: Windows.
- Python: CPython 3.12.10, 64-bit.
- Primary requirements installed from `requirements.txt`: beautifulsoup4 4.12.3, fastapi 0.115.0, httpx 0.27.2, matplotlib 3.9.2, nltk 3.9.1, prometheus-client 0.21.0, pydantic 2.9.2, pytest 8.3.3, python-dotenv 1.0.1, streamlit 1.43.0, uvicorn 0.30.6.
- Test plotting backend: Matplotlib `Agg`, set by `tests/conftest.py` and CI environment.
- NLTK WordNet: unavailable in this temporary environment. `app.preprocessing` therefore used its implemented tokenization fallback without lemmatization. Evaluation results can differ when WordNet is installed.
- `VECTOR_STORE_BACKEND=local`; retrieval benchmark uses its own in-script keyword and lexical term-frequency cosine retrievers, not Chroma or dense embeddings.
- No API keys, Chroma installation, downloaded embedding model, NLLB model, Ollama service, or vision API were used.
- Docker CLI was not available, so no image build or container runtime is claimed.
- The documented Uvicorn factory command was started in a disposable sample-only project copy with the local vector backend. `/health` returned `ok`; medical and research `POST /chat` requests returned HTTP 200 with sources. This verifies the application factory and sample data path, not Docker packaging.

## Commands

The final full suite was run from the repository after evaluation tests were updated to use `tmp_path` and API tests injected sample domain services. Headless Matplotlib was configured explicitly:

```powershell
$env:MPLBACKEND = "Agg"
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" -m pytest -q
```

`tests/conftest.py` also selects `Agg` for pytest runs.

Baseline scripts were run with the isolated Python 3.12 environment and an explicit versioned destination:

```powershell
$env:MPLBACKEND = "Agg"
$env:VECTOR_STORE_BACKEND = "local"
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" experiments/run_benchmark.py --results-dir docs/evaluation/baseline-2026-09-26
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" experiments/run_sentiment_evaluation.py --results-dir docs/evaluation/baseline-2026-09-26
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" experiments/run_multilingual_evaluation.py --results-dir docs/evaluation/baseline-2026-09-26
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" experiments/run_multimodal_benchmark.py --results-dir docs/evaluation/baseline-2026-09-26
```

The temporary venv path is machine-specific. For a normal setup, create a Python 3.12 venv, install `requirements.txt`, activate it, then run the same module commands with `python`.

## Dataset and Results

### Retrieval benchmark

- Dataset: `experiments/benchmark_dataset.json`, 5 queries; configured local knowledge corpus contains company handbook, product updates, and security playbook. Remote Python news is explicitly excluded by `build_chunks(..., include_remote=False)`.
- Both variants use top 3 results and 220-character chunks. `KeywordOverlap` uses zero overlap; `CosineOverlap` uses 60-character overlap. The second variant is still lexical cosine over term counts, not dense embedding retrieval.

| Variant | Source top-1 | Source top-3 | Mean expected-keyword recall |
|---|---:|---:|---:|
| KeywordOverlap | 1.000 | 1.000 | 0.800 |
| CosineOverlap | 1.000 | 1.000 | 0.733 |

All five queries retrieved the expected source at rank 1. Per-query expected-keyword recall was:

| Query | KeywordOverlap | CosineOverlap |
|---|---:|---:|
| How does the chatbot learn about new information over time? | 1.000 | 1.000 |
| Can the system refresh the knowledge base automatically as well as manually? | 1.000 | 1.000 |
| What headers protect public chat access and admin operations? | 0.500 | 0.500 |
| What happens if the language model is down? | 0.500 | 0.500 |
| What operational data can users inspect from the service? | 1.000 | 0.667 |

Historical checked-in `artifacts/benchmark_results.json` reports keyword recall `0.800` and `0.833` for those variants. This fresh run reproduced `0.800` and `0.733`. The second aggregate is therefore not reproducible from the current code/data/environment used here. Source accuracy is source-level and hides missing expected content. See [retrieval_results.json](retrieval_results.json) and [retrieval_per_query.json](retrieval_per_query.json).

### Sentiment evaluation

- Dataset: `dataset/sentiment_evaluation.json`, 10 examples: 3 positive, 3 negative, 4 neutral.
- Accuracy: `0.800`.
- Macro F1: `0.806`.
- Deterministic response-prefix appropriateness: `1.000`; this tests adapter rules, not user satisfaction.
- See [sentiment_evaluation_results.json](sentiment_evaluation_results.json) and [sentiment_evaluation.png](sentiment_evaluation.png).

### Language evaluation

- Dataset: `dataset/multilingual_evaluation.json`, 8 examples; all eight have expected language `en`.
- Language accuracy: `1.000`.
- Normalized retrieval-term recall: `1.000`.
- These examples do not evaluate Spanish, Hindi, Bengali, code-switching, or NLLB translation.
- See [multilingual_evaluation_results.json](multilingual_evaluation_results.json).

### Multimodal evaluation

- Dataset: `experiments/multimodal_benchmark_dataset.json`, 4 rows; 3 unique referenced PNG files.
- All three paths (`release_board.png`, `security_alert.png`, `dual_schedule.png`) are missing from `dataset/visual_cases/` in this checkout. No sidecars or live vision endpoint were available.
- The runner marks the `MultimodalReasoner` results `blocked_missing_image_assets`. Its `0.000` keyword recall, `0.750` clarification accuracy, and `0.500` validator-grounded rate are missing-image fallback behavior only, not image-understanding metrics. One missing-image path response is considered grounded by the heuristic validator, demonstrating why that rate is not a factuality measure.
- The text-only fallback results on these image-specific prompts are also `0.000` keyword recall, `0.750` clarification accuracy, and `0.000` validator-grounded rate; this is not a fair text-vs-image quality comparison.
- See [multimodal_results.json](multimodal_results.json) and [multimodal_per_query.json](multimodal_per_query.json).

## Historical Artifact Preservation

The existing files under `artifacts/` were not overwritten. All evaluation scripts now accept `--results-dir` and default to this dated report directory. Pytest evaluation tests pass temporary output directories and do not modify historical benchmark files. The full datasets also remain unchanged.

## Data Availability and Docker

- Full MedQuAD: 11,306 XML files, approximately 50,170,614 bytes in this checkout. Optional for basic service startup; the bundled JSON sample supports the medical mode fallback.
- Full arXiv snapshot: approximately 5,422,885,483 bytes. Optional for basic service startup; the bundled 461-byte JSONL sample supports the research mode fallback.
- The Docker ignore policy excludes `data/`, the full datasets, and `.env`; it permits only `dataset/medquad_sample/sample_medquad_records.json` and `dataset/arxiv_sample/sample_arxiv_cs.jsonl`.
- Docker is unavailable on this audit machine; Docker context contents were configured but image build, embedded sample verification, and runtime are **not verified**.
- The API's service constructors already fall back to the sample paths and return a no-records answer if no dataset records are loaded. Tests cover the no-records response. General chat does not depend on the medical/arXiv corpora.

## Test Result

The latest full-suite result is **29 passed, 0 failed, 0 skipped, 0 errors** in 9.35 seconds, with 15 upstream deprecation warnings. The command was:

```powershell
$env:MPLBACKEND = "Agg"
& "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" -m pytest -q
```

The initial baseline before the Milestone 1 fix was `24 passed, 1 failed`; the failure was the medical entity casing mismatch. The later full suite ran from the repository after evaluation tests were made non-destructive and API tests switched to sample datasets.
