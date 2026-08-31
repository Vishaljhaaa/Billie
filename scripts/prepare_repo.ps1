# PowerShell helper to prepare the repository for publishing to GitHub
# Usage: Run from project root in PowerShell (not as Administrator unless needed)

Set-StrictMode -Version Latest
Write-Host "Preparing repository for publish..."

# Remove large or local-only folders from the index (but keep them on disk)
$paths = @(
  'dataset',
  'data',
  'artifacts'
)

foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Host "Removing $p from git index (keeps local files)..."
    git rm -r --cached $p -q 2>$null || Write-Host "No tracked items under $p"
  }
}

Write-Host "Adding recommended .gitignore entries and staging changes..."
git add .

Write-Host "Done. Review changes with 'git status' and 'git diff --staged' before committing."
Write-Host "If you need to remove large files from history, consider using 'git filter-repo' or the BFG repo-cleaner." 