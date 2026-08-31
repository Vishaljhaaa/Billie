# Helper script to run the demo on Windows PowerShell
# Usage: Open PowerShell in the project root and run:
#   .\scripts\run_demo.ps1

try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force -ErrorAction Stop
} catch {
    # If this fails, continue — activation may still work depending on policy
}

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . ".\.venv\Scripts\Activate.ps1"
} elseif (Test-Path ".\.venv\Scripts\activate.bat") {
    cmd /c ".venv\Scripts\activate.bat"
}

$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/demo_chat.py
