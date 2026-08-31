# Dataset Package

This folder contains the data assets used by the multimodal extension of the same chatbot training project.

## Files included

- `company_handbook.txt`: text knowledge about update and support workflows
- `product_updates.txt`: product and rollout notes
- `security_playbook.txt`: security procedures and escalation guidance
- `benchmark_dataset.json`: retrieval benchmark questions for the text pipeline
- `visual_cases/`: sample image inputs for multimodal reasoning

## Visual cases

The `visual_cases` folder contains:

- `.png` files used as image inputs
- matching `.json` sidecars with extracted evidence, entities, OCR text, ambiguity notes, and confidence scores

These sidecars make the multimodal benchmark reproducible even when a live vision API is not configured.

## Purpose

- The text files remain the base corpus from the original training project.
- The image cases are an internship-stage extension on top of the same assistant domain.
- No unrelated dataset or fresh standalone project was introduced.
