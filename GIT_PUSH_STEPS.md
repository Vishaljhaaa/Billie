# Git push steps (one-liners you can run locally)

Replace `your-remote-url` with `https://github.com/Vishaljhaaa/Billie.git` or your fork.

```bash
git init
git add .
git commit -m "chore: initial import; add demo, README, Dockerfile, CI"
git branch -M main
git remote add origin your-remote-url
git push -u origin main
```

If any large files were accidentally added, remove them before pushing:
```bash
git rm --cached path/to/largefile
git commit -m "chore: remove large dataset"
git push
```
