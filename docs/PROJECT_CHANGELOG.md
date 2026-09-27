# Project Change Log

## 2026-09-27

- Audited the current Milestone 2 retrieval integration against the authoritative plan in [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and the historical technical state in [PROJECT_TECHNICAL_LOG.md](../PROJECT_TECHNICAL_LOG.md).
- Confirmed the repository contains the current Milestone 2 BM25 and retrieval-mode integration in [app/retrieval.py](../app/retrieval.py), [app/vector_store.py](../app/vector_store.py), and [app/config.py](../app/config.py), with focused validation in [tests/test_retrieval.py](../tests/test_retrieval.py) and [tests/test_chatbot.py](../tests/test_chatbot.py).
- Verified the current repo state reports 11 targeted passing tests: Milestone 2 retrieval wiring and chatbot behavior checks are passing in the current checkout.
- Audit finding: this satisfies the narrow Milestone 2 integration subset and the current retrieval smoke checks, but it does not yet satisfy the full Milestone 2 acceptance criteria in [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), which still require dense-index verification, RRF/hybrid evaluation, metadata and compatibility checks, source-removal semantics, and the frozen labeled evaluation dataset/reporting before the milestone can be considered fully complete.
- No implementation code was changed during this audit; this log entry records the audit state only and awaits approval for the next controlled step.

### 2026-09-27 — Milestone 2 acceptance audit follow-up

- Reviewed the outstanding acceptance criteria in [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and the historical execution record in [PROJECT_TECHNICAL_LOG.md](../PROJECT_TECHNICAL_LOG.md) without changing runtime behavior.
- Verified that the current repository has passing focused retrieval/chat tests, but that the plan still requires: a frozen relevance-labeled retrieval dataset, same-dataset BM25/dense/hybrid comparison on Recall@K/MRR/nDCG, latency/indexing measurements, metadata-preserving RRF checks, incremental-source update/removal/restart validation, and explicit dense-backend fallback compatibility evidence.
- Distinguished previously reported historical benchmark claims from verified current evidence: the historical artifact remains a legacy source-level table, while the current code and tests do not yet establish a same-set improvement claim for BM25 or hybrid mode.
- This audit remains approval-gated and does not start Milestone 3 or any implementation or evaluation work.

### 2026-09-27 — Retrieval-v1 specification only (no implementation or benchmark execution)

- Inspected the existing Milestone 2 plan in [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), the historical technical record in [PROJECT_TECHNICAL_LOG.md](../PROJECT_TECHNICAL_LOG.md), and the current retrieval-v1 dataset artifacts in [experiments/datasets/retrieval-v1/metadata.json](../experiments/datasets/retrieval-v1/metadata.json) and [experiments/datasets/retrieval-v1/queries.jsonl](../experiments/datasets/retrieval-v1/queries.jsonl).
- Confirmed the repository already contains a draft retrieval-v1 dataset and metadata that are source-anchored but explicitly not yet human-reviewed or frozen as a portfolio-grade benchmark.
- Added the dataset/evaluation specification in [experiments/datasets/retrieval-v1/README.md](../experiments/datasets/retrieval-v1/README.md). It defines the schema, relevance-grade rules, split policy, same-dataset comparison matrix, metric requirements, latency/reporting requirements, and freeze/review rules without modifying runtime code or running any benchmark.
- This specification step remains approval-gated and does not execute retrieval work, install dependencies, download models, contact external services, or begin Milestone 3.

### 2026-09-27 — Retrieval-v1 review-preparation archive and reviewer sidecar

- Verified the exact approved local source files in [knowledge/company_handbook.txt](../knowledge/company_handbook.txt), [knowledge/product_updates.txt](../knowledge/product_updates.txt), and [knowledge/security_playbook.txt](../knowledge/security_playbook.txt), and copied them byte-for-byte to [experiments/datasets/retrieval-v1/source-snapshots](../experiments/datasets/retrieval-v1/source-snapshots) without modifying the original runtime code, dataset annotations, or source files.
- Generated and verified the SHA-256 snapshot manifest at [experiments/datasets/retrieval-v1/source-snapshots/snapshot_manifest.json](../experiments/datasets/retrieval-v1/source-snapshots/snapshot_manifest.json) against the archived bytes. Verified hashes:
  - company-handbook: 13A0D2D6A4EADB5745EDD9D7CF4B8368371E6EA399E4A3AC4B875BDCE343F358
  - product-updates: E8BB0C518BA5CA9B3F78378812BF602928E2C362B9741D2D39146A36E3D1CEBD
  - security-playbook: A09A1B30B2DA005FC82D4EF63A341B1D197E7D31B5CF8D0A9394CABE7CF610EA
- Created the review-preparation sidecar in [experiments/datasets/retrieval-v1/review](../experiments/datasets/retrieval-v1/review): [review_checklist.md](../experiments/datasets/retrieval-v1/review/review_checklist.md), [reviewer_decisions.jsonl](../experiments/datasets/retrieval-v1/review/reviewer_decisions.jsonl), and [review_summary.json](../experiments/datasets/retrieval-v1/review/review_summary.json).
- Kept the original dataset files unchanged: [experiments/datasets/retrieval-v1/queries.jsonl](../experiments/datasets/retrieval-v1/queries.jsonl) and [experiments/datasets/retrieval-v1/metadata.json](../experiments/datasets/retrieval-v1/metadata.json).
- Recorded the dataset status as diagnostic-only and not independently reviewed or frozen. This review-preparation step does not run benchmarks, install dependencies, exercise external sources, or begin Milestone 3.
