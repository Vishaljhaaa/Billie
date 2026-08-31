# Publish & Repo Hygiene Guide

Follow these steps to prepare the project for publishing to GitHub and keep the repository lightweight and safe.

1) Inspect large files currently tracked (run locally)

```powershell
# List tracked files with sizes (Windows PowerShell)
git ls-tree -r -l HEAD | sort -k4 -n -r | Select-Object -First 50

# Or to find large objects in history (Unix-style, works in Git Bash / WSL):
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | sed -n 's/^blob //p' \
  | sort -n -k2 -r \
  | head -n 50
```

2) Prepare the working tree (remove data/artifacts from the index)

Use the included helpers to untrack large local directories while keeping the files on disk:

PowerShell (recommended on Windows):
```powershell
.\scripts\prepare_repo.ps1
```

Bash (macOS / Linux / Git Bash):
```bash
bash ./scripts/prepare_repo.sh
```

3) Commit the trimmed index

```powershell
git add .
git commit -m "chore: remove large local data from index before publish"
```

4) (Optional) Remove large files from git history

If large files were already pushed and you need to remove them from history, use one of these tools:
- `git filter-repo` (recommended)
- BFG Repo-Cleaner (`bfg`)

Example with `git filter-repo` (install via pip):

```bash
pip install git-filter-repo
git filter-repo --invert-paths --paths dataset/ --paths data/ --paths artifacts/
```

Warning: rewriting history changes commit SHAs. Coordinate with teammates and only perform on repos where you control remotes.

5) Push to GitHub

Set or update the `origin` remote and push:

```powershell
git remote set-url origin https://github.com/Vishaljhaaa/Billie.git
git push -u origin main
```

If authentication fails, use `gh auth login` or configure the credential helper:

```powershell
gh auth login
# or
git config --global credential.helper manager-core
```

6) Use Git LFS for large assets going forward

If you need to keep large binaries in the repo, use Git LFS:

```powershell
git lfs install
git lfs track "dataset/**"
git add .gitattributes
git add dataset/*
git commit -m "chore: add LFS tracking for dataset"
git push
```

7) Verify CI & Docker

- Check GitHub Actions on push (workflow is in `.github/workflows/ci.yml`).
- If you published an image or want Docker on CI, ensure the `Dockerfile` is correct and avoid copying dataset into the image.

If you'd like, I can:
- Run the prepare script modifications in the repo (I created `scripts/prepare_repo.ps1`), or
- Walk you through the exact terminal commands to run on your machine and confirm the push.

Paste the output of `git status` and `git remote -v` if you want me to verify the next steps before pushing.
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
