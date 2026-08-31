# Publishing Guide

This document shows recommended steps to prepare and push this repository to GitHub with good hygiene.

1. Review `.gitignore` to exclude large data and local state (already added).
2. Create a repository on GitHub named `Billie` (or your preferred name).
3. Initialize git, add files, and commit locally:
```bash
git init
git add .
git commit -m "chore: initial project import with README, demo scripts, Dockerfile, CI"
```
4. Add remote and push:
```bash
git remote add origin https://github.com/Vishaljhaaa/Billie.git
git branch -M main
git push -u origin main
```
5. After pushing, enable GitHub Actions (CI) and verify tests run on the CI page.

Notes on large files
- Remove any large dataset files from the repo (they should be downloaded on-demand or stored in release assets). Use `git rm --cached <file>` before commit if necessary.
- For historical large files, use `git filter-repo` or `git lfs` when appropriate.
