# Retrieval v1 dataset and evaluation protocol

## Scope and authority

This specification is the authoritatively scoped dataset and evaluation protocol for Milestone 2 retrieval work. It is derived from the existing plan in [docs/IMPLEMENTATION_PLAN.md](../../../docs/IMPLEMENTATION_PLAN.md) and the historical technical record in [PROJECT_TECHNICAL_LOG.md](../../../PROJECT_TECHNICAL_LOG.md).

The purpose of this document is to define the expected dataset contract, relevance labeling protocol, same-dataset comparison matrix, metric/reporting requirements, and freezing rules before any implementation or performance claim. It does not change application runtime code or retrieval behavior.

## 1. Dataset scope and frozen corpus

### 1.1 Corpus and source boundary

The retrieval-v1 dataset is intentionally limited to the three checked-in local knowledge files in the repository and excludes the dynamic Python-news source until it has a byte-identical, hash-verified snapshot. This mirrors the plan’s requirement that the current local corpus is too small for statistically powered generalization and that dynamic remote content cannot be counted as labeled evidence without a frozen snapshot.

Allowed local sources for this version:
- company-handbook
- product-updates
- security-playbook

Excluded from this version:
- python-news URL and cached remote chunks
- any crawled article pages or retrieved remote pages not retained as frozen source snapshots

### 1.2 Source snapshot contract

Every query and label must bind to a source ID and a source fingerprint. The source fingerprint must be computed from the exact frozen file bytes used to build the retrieval corpus.

Required fields for each source in the dataset metadata:
- source_id
- path
- sha256
- bytes
- factual_sentence_units
- chunking configuration used for the frozen corpus

The dataset metadata file is:
- [experiments/datasets/retrieval-v1/metadata.json](metadata.json)

The active query file is:
- [experiments/datasets/retrieval-v1/queries.jsonl](queries.jsonl)

## 2. Data schema

### 2.1 Query object schema

Each JSON object in `queries.jsonl` is a single retrieval query record. Required keys:

- query_id: stable ID, unique in the dataset
- query: natural-language retrieval query string
- query_type: one of
  - exact_keyword
  - paraphrase
  - multi_source
  - ambiguous_multi_passage
  - unanswerable_missing_number
  - unanswerable_missing_date
  - unanswerable_missing_count
  - unanswerable_missing_entity
  - unanswerable_missing_location
  - unanswerable_missing_technical_detail
- answerability: `answerable` or `unanswerable`
- evidence_cluster: cluster ID shared by paraphrases of the same fact or evidence unit
- split: `development` or `test`
- relevant_passages: array of passage labels
  - source_id
  - quote: verbatim source quote used as the anchor
  - relevance: integer grade 0, 1, or 2
  - note: optional free-form annotation details

For unanswerable records, `relevant_passages` must be empty and the record should include a human-written explanation such as `unanswerable_reason`.

### 2.2 Relevance grades

The relevance grade is defined exactly as the plan requires:
- 0 = irrelevant
- 1 = useful context
- 2 = directly answers the query

Only source-grounded facts are eligible for answerable labels. Labels must never be inferred from a model response or from a guessed answer. They must be anchored to a specific source quote and source fingerprint.

### 2.3 Evidence clusters

Evidence clusters are groups of paraphrases that refer to the same source fact. The split policy is:
- All paraphrases for the same evidence unit stay in the same split.
- If a query requires multiple passages jointly to answer, it remains grouped in one evidence cluster and must be held out as a multi-passage combination only if that combination is needed for the answer.
- Unanswerable probes remain separate and are not used in answerable-query recall or MRR computations.

This prevents leakage between development and test splits when the corpus is tiny.

## 3. Annotation protocol

### 3.1 Annotation source and rules

All labels must be created by reviewing the exact source text in the frozen local knowledge files. No expected answer text is stored in the dataset. That means the dataset records the evidence anchor, not a generated answer string.

Required annotation steps:
1. Read the full source file for the relevant source.
2. Identify the exact sentence or sentence fragment that supports the fact.
3. Record the verbatim quote and source_id.
4. Set the relevance grade to 2 if it directly answers; 1 if it is useful context; 0 if irrelevant.
5. If the query is unanswerable, verify there is no fact in the frozen corpus that supports it.
6. Record the answerability and evidence_cluster fields before evaluation.

### 3.2 Reviewer policy

The plan requires a second reviewer for held-out labels and a sample of development labels. This document adopts the plan’s current status: the existing retrieval-v1 dataset is a source-anchored draft and must not be treated as a fully reviewed benchmark until the review step is completed.

Required review workflow:
- Primary annotator writes the source-anchored labels.
- Second reviewer checks all test-set labels and a sample of development-set labels.
- Disagreements are explicitly logged as annotation notes or a review file.
- Only frozen, resolved labels are eligible for comparison reports.

If no second reviewer is available, the dataset remains a diagnostic annotation set and must be reported as not human-reviewed.

### 3.3 Freeze and versioning policy

The dataset is versioned at the directory and metadata level.

Required metadata fields for versioning:
- dataset_id
- version
- created_on
- format
- source_scope
- source hashes
- tokenizer version
- chunker version
- review_status
- split method
- limitations

The frozen dataset is considered stable only when the following are fixed:
- source hashes
- tokenizer version
- chunking configuration
- question file and annotation content
- split assignments and evidence clusters
- review status

Any change to the corpus, chunker, tokenizer, or query set requires a new dataset version, not an in-place update to the existing v1 benchmark.

## 4. Evaluation matrix and report requirements

### 4.1 Same-dataset comparison matrix

The comparison matrix must evaluate the same frozen corpus, same queries, same chunk settings, and same dataset splits for each configuration. The required comparison rows are:

1. legacy keyword overlap
2. legacy local cosine fallback
3. existing Chroma dense baseline, only if the optional dependency/model is actually available and configured
4. BM25
5. BM25 + dense RRF
6. reranking only if the hybrid results justify it

This matrix must be run on the exact same dataset and the same retrieval-v1 frozen source snapshot. No alternative corpus or remote source is allowed.

### 4.2 Metrics

The plan sets the required metrics:

- Recall@K
  - $Recall@K = |relevant items in top K| / |all labeled relevant items|$
  - Macro-averaged over answerable queries.
- MRR
  - Mean reciprocal rank of the first relevant result over answerable queries that have a relevant item.
- nDCG@K
  - Normalized discounted cumulative gain using relevance grades with gain $2^relevance\_grade - 1$ and rank discount $log_2(rank + 1)$.
- Answerable vs. unanswerable handling
  - Unanswerable queries are excluded from answerable-query recall/MRR/nDCG,
  - but they are reported separately as candidate-return rate and misleading-evidence rate.

### 4.3 Retrieval latency and indexing cost requirements

The evaluation report must separate retrieval-only performance from generation latency.

Required measurements:
- retrieval-only warm and cold p50/p95 latency
- indexing or build time
- active backend/model/index configuration
- process memory where feasible
- active tokenizer and chunking configuration
- source fingerprint and dataset version

No generation latency or LLM response latency may be mixed into retrieval metrics.

### 4.4 Report outputs

The report should include at least:
- aggregate metrics by method
- per-query results
- answerable and unanswerable breakdowns
- corpus metadata and frozen source hashes
- backend configuration snapshot
- retrieval latency summaries
- failure categories and missing dependencies

The output should be machine-readable where practical, such as JSON and CSV/JSONL, and should preserve the historical benchmark as a separate artifact rather than replacing it.

## 5. Reproducibility requirements

### 5.1 Frozen evaluation rules

No benchmark claim is valid unless it is produced from the same:
- frozen source files
- source hashes
- tokenizer
- chunking configuration
- query set
- data split
- backend state
- evaluation script version

A benchmark is not considered comparable if it changes any of the above elements without a new version identifier.

### 5.2 No claim of improvement without same-set comparison

Any improvement claim must be supported by the same-dataset comparison on the same retrieval-v1 evaluation set. It is not enough to show one method is better on a different benchmark or with a different corpus.

This specification intentionally prohibits:
- generating benchmark claims from historical artifact values alone
- comparing different corpora or different chunking/regimes without a new dataset version
- claiming retrieval improvement or model superiority without exact same-set output

### 5.3 External dependencies and offline safety

This protocol does not require, and must not trigger:
- model downloads
- external service access
- Chroma dependency installation
- reranker or cross-encoder download
- remote URL fetches for the Python-news source

The evaluation pipeline remains offline and model-free unless a separate, explicit approval exists for optional backend testing.

## 6. Review and freeze policy

### 6.1 Data review gates

The retrieval-v1 dataset should be treated as the following:
- Diagnostic benchmark: valid for implementation iteration and local validation
- Portfolio-grade benchmark: only after independent review and freeze

The plan’s minimum review gate is:
- second reviewer checks all test labels and a sample of development labels
- disagreements are logged and resolved
- dataset metadata records the final review status

### 6.2 Freeze status

As of this specification, the repository contains a draft retrieval-v1 dataset and metadata, but the plan still requires independent human review and final freeze before the dataset can be used as the definitive acceptance benchmark.

## 7. Remaining decisions requiring approval

The following items remain open before the dataset is treated as a human-reviewed benchmark or before proceeding with the implementation/evaluation phase:

1. Second reviewer availability for label confirmation.
2. Whether the Python-news source is allowed into the benchmark only after a hash-verified snapshot is archived and reviewed.
3. Whether the current retrieval-v1 set remains a diagnostic-only dataset until broader corpus approval is granted.
4. Whether dataset expansion beyond the current three local sources is approved for a future version.

## 8. Spec status

This is the complete dataset/evaluation specification step only. It does not change application code, change retrieval defaults, install dependencies, run benchmarks, or start Milestone 3.
