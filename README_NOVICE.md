**Project: Unified AI Chatbot — Quick Start for Novice Users**

This guide explains, in simple steps, how to run the project locally or in Docker, what the app does, and how to interpret results. It assumes you have a Windows machine and minimal command-line familiarity.

**What it does:**
- **Retrieval-first chatbot**: the app searches the knowledge files for relevant passages, optionally calls an LLM to compose an answer, and returns the answer plus the list of supporting sources and a validation flag that shows whether the answer is grounded in retrieved evidence.

**Three simple ways to run it (pick one)**

**1) Streamlit GUI**
- Prerequisite: Python 3.12 installed.
- From a fresh PowerShell in the project root:
```powershell
cd path\to\project
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```
- Open your browser at http://localhost:8501 and type questions into the UI.

**2) Quick CLI demo script (no browser needed)**
- Good for a quick check or when showing the JSON output to someone.
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python .\scripts\demo_chat.py
```
- Output format example:
```json
{
  "answer": "The chatbot updates its vector database on a schedule and also supports manual sync.",
  "sources": ["knowledge/company_handbook.txt"],
  "used_llm": false,
  "validation": { "grounded": true }
}
```

**3) Run the API (for integrations)**
- Start the FastAPI server (the app factory lives in `app/main.py`):
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```
- Example request (POST `/chat`): see `FRONTEND_USAGE.md` for a sample payload. The response uses the same JSON structure as the CLI demo.

**Run offline tests**

From the activated Python 3.12 environment, run:
```powershell
python -m pytest -q
```

Tests do not need API keys or optional downloaded models.

**Docker**

The Dockerfile runs only FastAPI on port 8000; Streamlit is run separately with the command above. The image includes small medical and arXiv fallback samples, not the full MedQuAD or 5.4 GB arXiv data. Docker builds have not been verified in the current development environment.

```powershell
docker build -t billie:local .
docker run --rm -p 8000:8000 --env-file .env billie:local
```

**How to interpret what you see**
- **`answer`**: the chatbot's response.
- **`sources`**: list of documents/filenames used to support the answer — check these to verify claims.
- **`used_llm`**: `false` means the system returned a retrieval-only answer; `true` means an LLM was used.
- **`validation.grounded`**: a heuristic token-overlap result, not proof that the answer is factually correct.
- **`validation.issues`**: human-readable list of problems when grounded is `false` (e.g., "No supporting evidence was available for validation."). If you see "Needs Review" in the UI, treat the answer as unverified until you confirm the sources.

Screenshots: If you see the UI message "I couldn't find relevant text or visual evidence in the current knowledge base," try a different query or add more documents to the `knowledge/` folder.

**Common problems & fixes (Windows-specific)**
- Symptom: `Fatal error in launcher: Unable to create process using '...\\other_env\\.venv\\Scripts\\python.exe'` or commands like `pip`/`streamlit` fail.
  - Cause: a broken or different virtualenv was active when wrappers were created, or the `Scripts` wrappers point to a different Python installation.
  - Fix (fresh PowerShell session, run from project root):
```powershell
# close other shells, then in a new PowerShell
cd path\to\project
Remove-Item -Recurse -Force .venv      # only remove this project's broken environment
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
- Use module form (`python -m pip ...` and `python -m streamlit run ...`) to avoid stale `*.exe` wrappers.
- If Windows reports filesystem corruption, reboot and run `chkdsk C: /f` as administrator.

**How to customize the knowledge base (for novices)**
- Put plain text files (`.txt`, `.md`) or small JSON in the `knowledge/` folder.
- Run the project's updater (or run `scripts/demo_chat.py` if it triggers loading) to index new documents. If your setup uses Chroma or another vector store, follow `app/vector_store.py` comments for rebuilding the index.

**Quick checklist to hand to a novice user**
1. Install Python 3.12.
2. Open PowerShell and `cd` to the project.
3. Run the Streamlit flow (see above) and open http://localhost:8501.
4. Type a question; examine `sources` and `validation` details.

**Next steps I can do for you**
- Add a one-click PowerShell setup script to create the venv and start Streamlit.
- Create a short explainer email/tutorial you can send to coworkers.

If you want the one-click setup script, tell me whether you prefer PowerShell or a cross-platform `bash` script and I’ll add it.
