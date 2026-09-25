# Project Technical Log

**Snapshot date:** 2026-09-26  
**Scope:** Code-backed inventory of the project as it currently exists. This is a state-based technical log, not a chronological Git commit history.

## Project Summary

The project is a Python retrieval-augmented knowledge assistant with two application surfaces: a Streamlit chat interface and a FastAPI service. Its general assistant retrieves evidence from configured knowledge sources, can incorporate image evidence and recent conversation turns, and may use an OpenAI-compatible LLM to compose answers. Separate modes provide retrieval-based medical Q&A over MedQuAD and computer-science paper retrieval over arXiv metadata.

The main application wiring is in [app/main.py](app/main.py); the Streamlit interface is in [streamlit_app.py](streamlit_app.py). Runtime configuration and the default source list are in [app/config.py](app/config.py) and [sources.json](sources.json).

## Implemented Application Features

### General knowledge assistant

- Searches configured company handbook, product update, and security playbook sources, plus the configured Python news URL.
- Retrieves relevant text chunks through a persistent vector-store abstraction. Chroma with `all-MiniLM-L6-v2` is used when its optional dependencies are available; the project can instead use a persistent local JSON store with token-frequency cosine similarity.
- Filters weak or generic text-only retrieval matches before answering.
- Returns answer text together with source locations, evidence summaries, validation state, detected language and sentiment, and optional clarification information.
- Handles simple greetings without running retrieval or calling an LLM.
- Uses a deterministic evidence-based response fallback when no LLM is configured or an LLM request fails.

### Image and multimodal evidence

- The Streamlit UI accepts PNG, JPG/JPEG, and WebP uploads in general-assistant mode and stores them under `data/uploads/` using a content-derived filename.
- The vision layer reads JSON sidecar evidence when available. Otherwise, when an OpenAI-compatible model is configured, it can submit the image for analysis and request a JSON response containing a summary, evidence, entities, ambiguities, and confidence.
- When neither sidecar evidence nor a vision client is available, the system records limited image evidence based on the supplied description or path rather than claiming full image understanding.
- The reasoning layer detects ambiguity markers in image evidence and returns a follow-up question instead of silently choosing between interpretations.

### Conversation memory

- Chat turns are persisted as JSON by session ID, including the question, answer, source list, and visual summaries.
- The general chatbot uses a configurable recent-turn window as context for follow-up responses.
- Research mode includes recent questions in its retrieval query. The Streamlit research view uses the current UI history; the API reads recent turns from the persistent memory store.

### Medical Q&A mode

- Parses MedQuAD XML records and the bundled sample JSON data, retaining fields such as question type, focus, semantic type, source, and synonyms.
- Retrieves the best matching record using tokenized, lemmatized term vectors and cosine similarity, with a small question-type match bonus.
- Recognizes a fixed vocabulary of symptom, treatment, and disease terms and can include metadata-derived medical focus entities.
- Displays lexicon-derived entity labels in sentence case, preserves the dataset's canonical focus string, and deduplicates same-category matches case-insensitively.
- Returns the matched dataset answer, source, retrieval score, recognized entities, and an educational-information disclaimer.
- Does not diagnose, generate new clinical guidance, or replace a medical professional; the UI explicitly presents that limitation.

### arXiv computer-science research mode

- Loads arXiv JSON/JSONL metadata and filters for categories beginning with `cs.`; it limits loading to 5,000 papers by default and falls back to the bundled sample when the configured dataset yields no records.
- Retrieves up to three papers with a token-based cosine similarity search.
- Extracts candidate technical concepts, creates a short extractive abstract summary, and can produce a DOT-format concept graph.
- Uses retrieval plus extractive summaries by default. An optional Ollama connection can generate an explanation from the retrieved paper context.
- Displays matching papers and their identifiers, categories, publication date, authors, and summaries in the Streamlit UI.

### Language and sentiment adaptation

- Detects English, Spanish, Hindi, and Bengali using script checks and small deterministic lexicons; normalizes a limited set of terms to English for retrieval.
- Adds a language-specific answer prefix in the default mode. Full-sentence translation is available through an optional local NLLB model when `MULTILINGUAL_TRANSLATION_BACKEND=nllb` is configured and its dependencies/model are available.
- Classifies positive, negative, or neutral sentiment with a fixed word list, a short negation window, and an exclamation-mark adjustment.
- Adds a brief empathetic or appreciative prefix for negative or positive messages; neutral answers are left unchanged.

### Knowledge ingestion and refresh

- Supports local text files and remote HTML URLs through [app/sources.py](app/sources.py). HTML scripts, styles, and noscript content are removed before text extraction; URL requests have configurable timeouts and retries.
- Normalizes whitespace, chunks content with configurable overlap, and fingerprints normalized source text with SHA-256.
- Replaces indexed chunks only when a source fingerprint changes. Source fingerprints and update timestamps are persisted in SQLite.
- Performs an initial sync during FastAPI startup, then starts a background refresh scheduler when enabled. The Streamlit application runs its initial sync once per Streamlit session state.
- Supports manual refresh through the API and admin dashboard. Failed, skipped, and updated sources are reported separately.

### HTTP API, administration, and monitoring

The FastAPI service exposes:

- `GET /health` for a health response.
- `GET /` for a simple service overview page.
- `GET /metrics` for Prometheus-formatted metrics.
- `POST /chat` for general, medical, or research mode requests.
- `POST /sync` and `POST /admin/sync` for a manual source refresh.
- `GET /admin` for the admin page and `GET /admin/status` for indexed-source and sync status.

API chat authorization uses the `X-API-Key` header when `CHATBOT_API_KEY` is set. Admin operations use `X-Admin-Key` when `CHATBOT_ADMIN_API_KEY` is set. These checks are permissive when their respective secrets are unset, so deployments must configure keys when protected access is required.

The monitoring layer counts HTTP requests and latency, chat/image requests, clarification requests, language and sentiment labels, sync runs/failures, and LLM calls/failures. The metrics endpoint exposes Prometheus counters and histograms.

## Runtime Flow

For a general-assistant question, the current pipeline is:

1. Load configuration, build services, and synchronize configured knowledge sources.
2. Detect language and sentiment; handle simple greetings early.
3. Retrieve text evidence and, if images were supplied, load sidecar or model-generated visual evidence.
4. Read recent conversation memory and detect ambiguity in visual evidence.
5. Call the optional LLM with the question, retrieved evidence, visual observations, and recent conversation. If unavailable or unsuccessful, use the deterministic fallback answer path.
6. Apply sentiment/language adaptation, validate answer-to-evidence token overlap, and persist the turn.
7. Return the response with its sources, evidence, validation result, and any follow-up question.

Medical and research requests use their own dataset services rather than the general knowledge index. The FastAPI API returns a common `ChatResponse` shape for each mode, but the API's medical/research responses contain less diagnostic detail than the corresponding Streamlit displays.

## Data, Configuration, and Deployment

- Default source IDs and retrieval/scheduler settings: [sources.json](sources.json).
- Primary runtime settings include LLM credentials/model/base URL, API/admin keys, source retry values, and vector-store selection; see [.env.example](.env.example).
- Conversation memory is stored in JSON; source state is stored in SQLite; the vector index is stored under `data/chroma/` by default.
- Bundled data includes the three knowledge text files, MedQuAD content and sample data, arXiv metadata/sample data, and sentiment/language evaluation samples. The multimodal benchmark JSON references image fixtures under `dataset/visual_cases/`, but those files are absent from this checkout.
- [Dockerfile](Dockerfile) is configured to start the FastAPI service on port 8000. It does not start the Streamlit UI; Streamlit is separate. `.dockerignore` now allows only the small medical/arXiv fallback samples while excluding full corpora, mutable `data/`, and `.env`. Docker was unavailable, so image build/runtime are not verified.
- [.github/workflows/ci.yml](.github/workflows/ci.yml) configures GitHub Actions to install the primary requirements and run `pytest` on Python 3.12 with the Matplotlib `Agg` backend for pushes and pull requests to `main` or `master`.
- The documented FastAPI factory invocation is `python -m uvicorn app.main:create_app --factory`. The novice and developer setup guides were corrected to use the factory; no module-level `app` object exists.

## Tests and Evaluation Evidence

The test suite is organized around API behavior, chatbot behavior, source loading, preprocessing, medical Q&A, arXiv retrieval, sentiment, multilingual handling, evaluation scripts, and retrieval benchmarking. Relevant files are under [tests](tests).

Existing saved results in [artifacts](artifacts) report:

- **Retrieval benchmark:** both keyword-overlap and cosine-overlap variants report `1.0` top-1 and top-3 accuracy; average keyword recall is `0.800` and `0.833`, respectively.
- **Multimodal benchmark:** text-only and multimodal variants both report `0.0` average keyword recall; clarification accuracy is `0.75` for both; grounded rate is `0.0` and `0.5`, respectively. The benchmark references PNGs under `dataset/visual_cases/`, but that directory is absent in this checkout. The dated run labels the multimodal result `blocked_missing_image_assets`; these outputs are fallback behavior, not image-understanding evidence. It also shows a path-based fallback may be marked grounded by the token-overlap validator.
- **Fresh retrieval reproduction:** running the current benchmark in an isolated sandbox preserved the historical artifact and reproduced keyword-overlap at `1.0` top-1/top-3 and `0.800` keyword recall. The lexical cosine variant reproduced `1.0` top-1/top-3 but `0.733` keyword recall, rather than the historical artifact's `0.833`. The five-query per-example trace showed the expected source at rank 1 for all queries, while several expected-keyword recalls were only `0.5` to `0.667`.
- **Language evaluation:** the saved artifact reports `1.0` language accuracy and term recall over eight samples. The stored examples are all English, so this result does not verify Spanish, Hindi, or Bengali performance.
- **Sentiment evaluation:** the saved artifact reports `0.800` accuracy, `0.806` macro F1, and `1.0` response-appropriateness rate over ten samples. The appropriateness measure checks deterministic prefix behavior; it is not a user study.

Python 3.12.10 was installed using the Python Install Manager, and the pinned primary requirements were installed into a temporary venv outside the repository. The latest full suite ran with explicit `MPLBACKEND=Agg`: **29 passed, 0 failed, 0 skipped, 0 errors** in 9.35 seconds, with 15 upstream deprecation warnings. Command: `$env:MPLBACKEND='Agg'; & "$env:TEMP\billie-phase-zero-py312\Scripts\python.exe" -m pytest -q`. The previous medical casing failure is fixed. API tests inject small domain samples instead of parsing full corpora to test routing. NLTK WordNet data was absent, so tokenization used its documented no-lemmatization fallback. Historical files under `artifacts/` remain unchanged.

Current versioned evaluation outputs, environment details, per-query diagnostics, and exact commands are in [docs/evaluation/baseline-2026-09-26/REPORT.md](docs/evaluation/baseline-2026-09-26/REPORT.md). Evaluation scripts now default to the dated directory and accept `--results-dir`; tests direct generated outputs to temporary directories.

## Technical Limitations and Scope Notes

- Most language detection/normalization, sentiment analysis, medical entity extraction, and answer-grounding validation are rule/lexicon/token-overlap heuristics, not learned classifiers or formal guarantees.
- The default language path performs term substitution and language-prefix adaptation, not full translation. NLLB full-sentence translation is optional.
- The local vector-store fallback uses token-frequency cosine similarity rather than semantic embeddings. Dense embedding search depends on the optional Chroma/Sentence Transformers installation.
- Image inputs submitted through the API are filesystem paths that must be readable by the server. They are not uploaded as multipart file content by this API contract.
- `.dockerignore` now allows only `dataset/medquad_sample/sample_medquad_records.json` and `dataset/arxiv_sample/sample_arxiv_cs.jsonl` into the Docker context while excluding full datasets, mutable data, and `.env`. Docker is unavailable on this machine; image build and runtime remain unverified.
- `ResponseValidator` uses token overlap rather than claim entailment. Its result can be misleading for missing-image path fallbacks, and the LLM branch may retain validation computed before substituting a fallback answer.
- Medical answers are retrieved from the dataset and should be treated as educational content. The arXiv retriever is similarly lexical and only covers records loaded from the configured file/sample.
- API/admin authentication is only enforced when the corresponding environment key is configured.
- The saved benchmark outputs are small offline evaluations; they should not be presented as broad production-quality or user-satisfaction evidence.
- The README's stale suggestions to add a Dockerfile and GitHub Actions workflow were removed; both are already present in the project.

## Milestone 1 Verification

- Medical entity labels from the built-in lexicons are sentence case; metadata-provided focus text preserves its source casing. Same-category duplicates collapse case-insensitively. Regression tests cover categories, casing, canonical focus, duplicates, and empty data.
- The full test suite passes on Python 3.12.10; `pytest` and all pinned primary dependencies install from `requirements.txt`. Tests do not require API keys, external model services, Chroma, or large model downloads.
- Experiment scripts accept `--results-dir` and default to [docs/evaluation/baseline-2026-09-26/REPORT.md](docs/evaluation/baseline-2026-09-26/REPORT.md); historical `artifacts/` values remain separate and unchanged.
- FastAPI and Streamlit are documented as separate entry points. The FastAPI factory passed both `TestClient` tests and a live Uvicorn smoke test in a disposable sample-only copy: `/health` returned `ok`, and medical/research requests returned sources. Docker data allowlisting is configured but has not been tested by building an image.