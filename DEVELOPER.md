# Developer Notes

This file summarizes the project's runtime entrypoints, module responsibilities, and quick local run/checklist.

## Entrypoints
- `app/main.py`: FastAPI app factory (`create_app()`). Run with Uvicorn: `python -m uvicorn app.main:create_app --factory --reload`.
- `streamlit_app.py`: separate Streamlit UI app. Run with: `python -m streamlit run streamlit_app.py`.
- `experiments/*.py`: CLI experiment scripts (benchmark, multilingual, sentiment, multimodal).

## Key Modules & Responsibilities
- `app/config.py`: Loads `sources.json` and environment variables into `AppConfig` dataclass.
- `app/main.py`: Constructs service container and wires FastAPI endpoints (`/health`, `/chat`, `/sync`, `/admin`).
- `app/chatbot.py`: Retrieval and multimodal orchestration (language, sentiment, LLM calls, memory).
- `app/vector_store.py`: Abstracts vector backend (Chroma when available, JSON local fallback).
- `app/llm.py`: OpenAI-compatible client wrapper used for multimodal LLM calls.
- `app/vision.py`: Image evidence loader / sidecar handling and adapter to `EvidenceItem`.
- `app/memory.py`: Simple JSON-backed session memory store.
- `app/updater.py`, `app/sources.py`, `app/state.py`: Source ingestion, chunking, fingerprint state, and sync orchestration.
- `app/medical_qa.py`, `app/arxiv_expert.py`: Domain-specific dataset loaders and retrieval helpers.
- `app/preprocessing.py`, `app/text_utils.py`: Tokenization/lemmatization and text utilities (chunking, hashing).
- `app/validation.py`, `app/reasoning.py`, `app/sentiment.py`: Response validation, ambiguity detection, sentiment handling.
- `app/monitoring.py`: Prometheus metrics instrumentation.

## Environment & Dependencies
- Primary dependencies: listed in `requirements.txt`.
- Optional: `requirements-chroma.txt` for Chroma vector DB; `requirements-multilingual.txt` for NLLB/transformers.
- Important env vars:
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` — for LLM client
  - `CHATBOT_API_KEY`, `CHATBOT_ADMIN_API_KEY` — API/admin access control
  - `VECTOR_STORE_BACKEND=local` to force JSON local store

## Quick Local Checklist
1. Install Python 3.12, then create and activate a project virtual environment:
```
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Install deps:
```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
3. (Optional) For Chroma: `pip install -r requirements-chroma.txt`.
4. NLTK WordNet is optional. Without it, tokenization runs without lemmatization. To install it when network access is available:
```
python -m nltk.downloader wordnet
```
5. Run tests:
```
python -m pytest -q
```
6. Run the FastAPI app (factory):
```
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
7. Run the Streamlit UI:
```
python -m streamlit run streamlit_app.py
```

The Dockerfile runs only the FastAPI service. It includes the small MedQuAD and arXiv sample fallbacks; full corpora are not copied into the image. Docker build and runtime were not verified on the audit machine because Docker is unavailable.

## Troubleshooting Tips
- If retrieval behavior differs between machines, record whether WordNet data is installed; preprocessing intentionally falls back to tokenization without lemmatization.
- If vector results are empty, confirm `VECTOR_STORE_BACKEND` and that `data/chroma` or configured `vector_store_dir` is writable.
- The LLM and vision paths are optional and guarded by `config.llm.enabled` and presence of sidecar JSON files.

## Next actions you can ask me to do
- Re-run tests with verbose output and return failures.
- Run static analysis (`flake8` / `mypy`) and report issues.
- Install Chroma and run a small indexing smoke test.
