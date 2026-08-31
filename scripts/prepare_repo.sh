#!/usr/bin/env bash
# Pre-commit helper: trims dataset and large files before committing
# Run: bash scripts/prepare_repo.sh

git rm -r --cached dataset/ || true
git rm -r --cached data/chroma || true
git rm --cached artifacts/* || true
git add .
echo "Repository prepared for commit. Review `git status` before pushing."
