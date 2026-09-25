# Billie: Multimodal Knowledge Assistant

Billie is an existing Python retrieval-augmented assistant with a FastAPI API, a separate Streamlit UI, a general knowledge mode, and dataset-backed medical and arXiv research modes. It includes optional integrations for Chroma, OpenAI-compatible models, Ollama, and NLLB; these are not required for the offline test suite.

## Python 3.12 Setup

Create a virtual environment from the repository root and install the pinned primary dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

NLTK WordNet data is optional. If it is unavailable, preprocessing falls back to lowercase tokenization without lemmatization. This keeps tests usable offline but may change retrieval/evaluation results; record the resource state when comparing runs.

## Run Tests

```powershell
$env:MPLBACKEND = "Agg"
python -m pytest -q
```

`tests/conftest.py` also selects Matplotlib's non-interactive `Agg` backend; CI sets the same backend. Evaluation tests write only to temporary directories and do not overwrite the historical files under `artifacts/`.

## Run The Applications

Start the FastAPI service using the factory defined in `app/main.py`:

```powershell
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Run the Streamlit UI separately in another terminal:

```powershell
python -m streamlit run streamlit_app.py
```

The Dockerfile starts only FastAPI on port 8000. Docker build/runtime has not been verified on this machine because Docker is unavailable. The build context excludes `.env`, mutable `data/`, the full MedQuAD corpus, and the multi-gigabyte arXiv snapshot; it allows only the small medical and arXiv samples. Full datasets must be mounted/provided separately. If optional samples are absent, those domain modes return their existing no-records responses; the general assistant does not depend on them.

To build and run the API image on a machine with Docker:

```powershell
docker build -t billie:local .
docker run --rm -p 8000:8000 --env-file .env billie:local
```

Only include `.env` at runtime, never in the build context. Configure API/admin keys for protected use.

## Reproduce Offline Evaluations

All scripts default to `docs/evaluation/baseline-2026-09-26/`, leaving historical artifacts unchanged. Pass `--results-dir <path>` to select another output directory.

```powershell
$env:MPLBACKEND = "Agg"
$env:VECTOR_STORE_BACKEND = "local"
python experiments/run_benchmark.py --results-dir docs/evaluation/baseline-2026-09-26
python experiments/run_sentiment_evaluation.py --results-dir docs/evaluation/baseline-2026-09-26
python experiments/run_multilingual_evaluation.py --results-dir docs/evaluation/baseline-2026-09-26
python experiments/run_multimodal_benchmark.py --results-dir docs/evaluation/baseline-2026-09-26
```

The current multimodal dataset references image files that are absent from this checkout. Its result is marked `blocked_missing_image_assets` and is not evidence of image-understanding quality. The language evaluation currently has eight English-only examples; its result does not measure non-English accuracy. See [the versioned baseline report](docs/evaluation/baseline-2026-09-26/REPORT.md) for commands, versions, per-query details, metrics and blockers.

## Optional Backends

Install Chroma/Sentence Transformers from `requirements-chroma.txt` to request the Chroma vector store. Install `requirements-multilingual.txt` and set `MULTILINGUAL_TRANSLATION_BACKEND=nllb` to request full-sentence NLLB translation. OpenAI-compatible models require `OPENAI_API_KEY`; research explanations can use a separately running Ollama service. These optional paths are not exercised by the offline test suite.

## Problem Statement

This project extends my training-phase dynamic knowledge base chatbot into a multimodal AI assistant that can:

- reason over both text and image inputs
- retain conversational context across turns
- surface ambiguity instead of guessing
- validate whether a response is grounded in available evidence
- answer medical questions through a MedQuAD-based retrieval chatbot
- discuss computer science research papers through an arXiv expert chatbot
- detect customer sentiment and adapt chatbot responses to user emotion
- support multilingual conversations across English, Spanish, Hindi, and Bengali while preserving context

The internship extension stays on the same chatbot project and domain rather than switching to an unrelated dataset or a new standalone app.

It includes one unified Streamlit chatbot and one matching `/chat` API, with selectable modes for the general assistant, MedQuAD medical Q&A, and arXiv research expertise.

## Dataset

The repository includes the original chatbot knowledge corpus and sample datasets for the two domain modes. The multimodal benchmark's referenced image fixture directory is absent in this checkout.

### Text knowledge

- `knowledge/company_handbook.txt`
- `knowledge/product_updates.txt`
- `knowledge/security_playbook.txt`

### Retrieval benchmark

- `experiments/benchmark_dataset.json`

### Multimodal benchmark

`experiments/multimodal_benchmark_dataset.json` references three files under `dataset/visual_cases/`, but those images and sidecars are not present in this checkout. The current evaluation runner records the missing assets and labels that variant blocked; it does not provide evidence of image-understanding performance. Live image analysis is an optional, unverified OpenAI-compatible path.

### Medical QA data

Task 3 uses the MedQuAD dataset from `https://github.com/abachaa/MedQuAD`. Place the downloaded or cloned dataset at:

```text
dataset/MedQuAD/
```

The app also includes a small reproducible sample at `dataset/medquad_sample/sample_medquad_records.json` so the medical QA workflow can run before the full dataset is downloaded.

### arXiv CS research data

The arXiv expert can use the Kaggle arXiv metadata dataset from `https://www.kaggle.com/datasets/Cornell-University/arxiv`. The full snapshot is about 5.4 GB and is not required for startup. Place the downloaded metadata file at:

```text
dataset/arxiv/arxiv-metadata-oai-snapshot.json
```

The app filters to computer science categories such as `cs.CL`, `cs.LG`, `cs.CV`, and `cs.IR`. A small reproducible CS sample is included at `dataset/arxiv_sample/sample_arxiv_cs.jsonl` and is the dataset included in the Docker image.

## Methodology

### Base training project

The original training system already supported:

- incremental source ingestion
- fingerprint-based refresh
- chunking and retrieval
- optional LLM-backed answers
- admin sync and monitoring
- baseline vs improved retrieval benchmarking

### Internship extension

The new multimodal layer adds:

- `session_id`-based conversational memory via `app/memory.py`
- image evidence extraction via `app/vision.py`
- ambiguity detection and follow-up prompts via `app/reasoning.py`
- evidence-grounding checks via `app/validation.py`
- a multimodal benchmark comparing text-only fallback vs multimodal reasoning
- a MedQuAD medical QA module with XML parsing, retrieval, entity recognition, and a Streamlit UI
- an arXiv computer science expert module with paper retrieval, information extraction, summarization, follow-up context, concept visualization, and optional local open-source LLM explanations through Ollama
- a sentiment analysis layer that classifies positive, negative, or neutral user messages and adjusts answer tone
- a multilingual layer that detects language, handles mixed-language inputs, normalizes cross-lingual query terms, and keeps session memory across language switches

### Decision pipeline

1. Retrieve relevant text evidence from the indexed knowledge base.
2. Inspect provided image inputs using sidecar evidence or an optional vision model.
3. Pull recent session memory for conversational continuity.
4. Detect ambiguity before answering.
5. Generate an evidence-based answer through the multimodal reasoning layer.
6. Validate that the answer is grounded in the retrieved evidence.
7. Store the turn in memory for future follow-ups.

This design avoids simple one-shot generation from a single model and instead uses a small reasoning pipeline with retrieval, evidence extraction, memory, ambiguity handling, and response validation.

### Preprocessing

The retrieval pipeline now performs:

- whitespace normalization before chunking
- lowercase tokenization
- lemmatization with `WordNetLemmatizer` so related forms such as plural and singular terms are normalized before scoring

## Repository Structure

- `app/main.py`: FastAPI app and dependency wiring
- `streamlit_app.py`: unified Streamlit chatbot with general, medical, and arXiv modes
- `app/chatbot.py`: multimodal answer orchestration
- `app/medical_qa.py`: MedQuAD parser, medical retriever, and entity recognizer
- `app/arxiv_expert.py`: arXiv loader, retriever, summarizer, concept extractor, and optional local LLM client
- `app/sentiment.py`: customer sentiment detection and response adaptation
- `app/multilingual.py`: language detection, mixed-language handling, query normalization, and language-aware response adaptation
- `app/memory.py`: persistent session memory
- `app/vision.py`: image evidence extraction
- `app/reasoning.py`: ambiguity detection
- `app/validation.py`: response grounding checks
- `app/vector_store.py`: retrieval backend
- `app/updater.py`: source refresh pipeline
- `experiments/run_benchmark.py`: retrieval benchmark
- `experiments/run_multimodal_benchmark.py`: multimodal benchmark
- `tests/`: API, chatbot, source, and benchmark tests

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:create_app --factory --reload
```

Optional dense retrieval backend:

```bash
pip install -r requirements-chroma.txt
```

### Run the unified Streamlit chatbot

```bash
python -m streamlit run streamlit_app.py
```

Use the sidebar mode selector to switch between the general multimodal assistant, MedQuAD medical Q&A, and arXiv CS expert. The FastAPI `/chat` endpoint accepts the same modes through `"mode": "general"`, `"medical"`, or `"research"`.

To use a local open-source LLM for explanation generation, install and run Ollama, then set:

```bash
set OLLAMA_MODEL=llama3.1
```

The app still works without Ollama by using retrieval, information extraction, and extractive summarization.

### Enable full-sentence multilingual translation

The default multilingual path is deterministic and lightweight. To enable local, open-source NLLB translation for Spanish, Hindi, and Bengali queries and answers:

```bash
pip install -r requirements-multilingual.txt
set MULTILINGUAL_TRANSLATION_BACKEND=nllb
```

The first NLLB run downloads `facebook/nllb-200-distilled-600M`; keep the default backend for an offline demo without model downloads.

## API Usage

### Text-only request

```json
{
  "question": "How does the chatbot refresh its knowledge base?",
  "session_id": "demo-thread",
  "mode": "general"
}
```

### Multimodal request

```json
{
  "question": "Where should I report OTP phishing?",
  "session_id": "security-thread",
  "image_inputs": [
    {
      "path": "dataset/visual_cases/security_alert.png"
    }
  ]
}
```

Example PowerShell call:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://127.0.0.1:8000/chat `
  -Headers @{ "X-API-Key" = "chat-secret-123" } `
  -ContentType "application/json" `
  -Body '{
    "question":"Where should I report OTP phishing?",
    "session_id":"security-thread",
    "image_inputs":[{"path":"dataset/visual_cases/security_alert.png"}]
  }'
```

The response now includes evidence, validation status, and clarification flags in addition to `answer`, `sources`, and `used_llm`.

## Experiments

The offline evaluations are reproducible with `--results-dir` and now emit per-query JSON diagnostics. The current dated run and its limitations are documented in [docs/evaluation/baseline-2026-09-26/REPORT.md](docs/evaluation/baseline-2026-09-26/REPORT.md). The checked-in files in `artifacts/` are historical and are not overwritten by the test suite or the scripts' default output directory.

## MedQuAD Medical Q&A

The medical chatbot implements Task 3 inside the same repository:

- `MedQuADParser` reads MedQuAD-style XML files and extracts question, answer, focus, CUI, semantic type, question type, category, and synonyms where available.
- `MedicalQARetriever` uses lemmatized cosine retrieval over question-answer records.
- `MedicalEntityRecognizer` identifies basic symptoms, diseases, and treatment terms from the user question and matched MedQuAD focus.
- The unified `streamlit_app.py` provides a mode for asking medical questions and viewing the matched source, entities, and disclaimer.

This component is informational only and includes a medical safety disclaimer in every answer.

## arXiv Computer Science Expert

The arXiv expert chatbot implements a domain-specific research assistant:

- `ArxivDatasetLoader` reads the Kaggle arXiv metadata JSON-lines file and filters to computer science papers.
- `ArxivRetriever` uses lemmatized cosine retrieval over titles, abstracts, and categories.
- `ScientificNLP` extracts technical concepts, builds paper summaries, and creates a concept graph for visualization.
- `LocalOpenSourceLLM` can call an Ollama-hosted model such as `llama3.1` for explanation generation.
- The unified `streamlit_app.py` supports paper searching, follow-up questions, summaries, relevant paper panels, and concept visualization.

This module is runnable with the bundled CS sample and becomes much stronger when the full Kaggle arXiv metadata file is placed under `dataset/arxiv/`.

## Sentiment-Aware Chatbot

Task 5 is implemented in the main chatbot flow:

- `SentimentAnalyzer` classifies each user message as `positive`, `negative`, or `neutral`.
- The classifier uses lemmatized tokens, positive and negative lexicons, simple negation handling, and confidence scoring.
- `SentimentResponseAdapter` adjusts the response tone. For example, negative messages receive a more empathetic opening.
- Chat responses include a `sentiment` payload with label, confidence, and matched positive/negative cues.
- The Streamlit assistant shows detected sentiment and confidence for each response.

This helps the chatbot respond more appropriately during customer interactions and gives a measurable output for sentiment detection accuracy and response appropriateness.

### Sentiment evaluation

`dataset/sentiment_evaluation.json` is a labelled, balanced 18-message evaluation set. Run:

```bash
python experiments/run_sentiment_evaluation.py
```

It creates `artifacts/sentiment_evaluation_results.json` and `artifacts/sentiment_evaluation.png`, including accuracy, macro F1, per-class scores, and a response-appropriateness rate. The latter checks that negative messages get empathy, positive messages get acknowledgement, and neutral messages remain factual; it is an offline proxy, not a customer-satisfaction study.

## Multilingual Chatbot

Task 6 is implemented in the main chatbot flow:

- Supports English plus three additional languages: Spanish, Hindi, and Bengali.
- Detects language from script ranges and language-specific cue words.
- Handles mixed-language inputs such as English plus Hindi or Spanish terms.
- Normalizes key cross-lingual terms into English before retrieval so the same knowledge base can answer across languages.
- Preserves conversational continuity with the existing `session_id` memory store, even when the user switches languages across turns.
- Chat responses include a `language` payload with primary language, detected languages, confidence, normalized query, ambiguity flag, and notes.
- The Streamlit assistant shows detected language, confidence, and mixed-language status.

The default implementation is local and deterministic. It also includes an optional NLLB (`facebook/nllb-200-distilled-600M`) backend for full-sentence query translation before retrieval and answer translation after generation. This preserves the same session memory across language switches while providing genuine model-based cross-lingual handling when enabled.

### Multilingual evaluation

Run:

```bash
python experiments/run_multilingual_evaluation.py
```

This writes to the dated baseline directory by default. The current eight-row dataset contains English-only examples, so it measures neither non-English language detection nor translation quality.

## Testing

Run the full Python 3.12 suite:

```bash
python -m pytest -q
```

The test-only `Agg` Matplotlib backend is configured in `tests/conftest.py`. Benchmark/evaluation tests write results to pytest temporary directories. The latest verified result is recorded in the dated baseline report and this project log.

## Visual Outputs Included

The repo includes generated benchmark charts under the dated baseline directory:

- retrieval, sentiment, and multimodal fallback evaluation charts under `docs/evaluation/baseline-2026-09-26/`
- concept graphs and retrieved-paper panels rendered by the arXiv Streamlit mode

## Notes

- The multimodal benchmark currently has no image fixtures under `dataset/visual_cases/`; its fallback outputs are not image-understanding results.
- If `OPENAI_API_KEY` is set, the system can also call a vision-capable OpenAI-compatible endpoint for richer live image analysis.
- The project remains a direct extension of the training chatbot rather than a new unrelated dataset or application.
- The full MedQuAD dataset is not bundled here by default; place it under `dataset/MedQuAD/` to index the complete collection.
- The full Kaggle arXiv dataset is not bundled here by default; place `arxiv-metadata-oai-snapshot.json` under `dataset/arxiv/` to index the complete collection.

## Assumptions and Limitations

### Assumptions

- The task 1 base project is `elev/dynamically expanding chatbot memory`, and this repository is an extension of that same codebase.
- The original chatbot knowledge corpus remains the primary dataset, while the visual cases are an added multimodal extension in the same problem domain.
- Multimodal reasoning can be demonstrated reproducibly through image sidecar `.json` files when a live vision API is not configured.
- Recent-turn memory with a small fixed window is sufficient to demonstrate conversational continuity for this internship project.
- Rule-based ambiguity checks and heuristic grounding validation are acceptable for showing reasoning and decision-making behavior in a lightweight, reproducible system.

### Limitations

- The multimodal benchmark is intentionally small, so the reported results demonstrate capability on curated cases rather than broad real-world generalization.
- Offline image understanding depends on prepared sidecar evidence; richer live visual interpretation requires a configured `OPENAI_API_KEY`.
- Ambiguity handling is rule-based and may miss more subtle or complex uncertainty patterns.
- The response validator is heuristic, so it improves grounding checks but is not equivalent to a formal verifier model.
- Visual benchmark inputs referenced by the dataset are absent from this checkout.
- The bundled MedQuAD sample is only for smoke testing; full medical QA evaluation should use the complete MedQuAD dataset.
- The bundled arXiv sample is only for smoke testing; full research coverage requires the Kaggle arXiv metadata dataset.
- Multilingual support uses local detection and domain-term normalization, not full neural translation by default.
