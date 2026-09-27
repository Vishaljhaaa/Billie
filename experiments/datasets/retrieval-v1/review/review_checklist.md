# Retrieval-v1 reviewer checklist

Status: diagnostic-only, not independently reviewed or frozen.

## Scope

This checklist applies only to the three approved local source files in the retrieval-v1 corpus:
- company-handbook
- product-updates
- security-playbook

Python-news and all external sources remain excluded.

## Required checks for each query

1. Confirm the query is against the exact frozen corpus snapshot archived in `experiments/datasets/retrieval-v1/source-snapshots`.
2. Confirm the source file and source_id match the archived snapshot hash.
3. Verify the supporting quote is verbatim from the archived source bytes.
4. Confirm the relevance grade is:
   - 2 = directly answers the query
   - 1 = useful context only
   - 0 = irrelevant
5. If the query is unanswerable, confirm the fact is absent from the entire three-file corpus and not just absent from the current memory or assumptions.
6. Confirm all paraphrases of the same evidence unit stay within the same evidence cluster and same split.
7. Confirm test-set labels are reviewed and the development-sample labels are reviewed according to the current review policy.
8. Record any disagreement and do not overwrite the original annotation in `queries.jsonl`.

## Final decision states

- draft_not_reviewed
- in_review
- accepted_with_no_change
- accepted_with_revision
- rejected
- diagnostic_only
- frozen_after_review

## Important constraints

- Never mark this dataset as frozen, independently reviewed, or validated before the review and final adjudication are complete.
- Keep the original queries file and metadata file unchanged.
- Log decisions in a separate review sidecar, not in the original labels.
