**Project: Unified AI Chatbot — Quick Start for Novice Users**

This guide explains, in simple steps, how to run the project locally or in Docker, what the app does, and how to interpret results. It assumes you have a Windows machine and minimal command-line familiarity.

**What it does:**
- **Retrieval-first chatbot**: the app searches the knowledge files for relevant passages, optionally calls an LLM to compose an answer, and returns the answer plus the list of supporting sources and a validation flag that shows whether the answer is grounded in retrieved evidence.

**Three simple ways to run it (pick one)**

**1) Streamlit GUI (recommended for non-technical users)**
- Prereqs: Python 3.10+ installed.
- From a fresh PowerShell in the project root:
```powershell
cd C:\Users\Vishal\Desktop\project
py -3 -m venv .venv
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

**3) Run the API (for power users or integrations)**
- Start the FastAPI server (the app factory lives in `app/main.py`):
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:create_app --host 0.0.0.0 --port 8000
```
- Example request (POST `/chat`): see `FRONTEND_USAGE.md` for a sample payload. The response uses the same JSON structure as the CLI demo.

**Docker (one-line run for novices)**
- Build and run (choose port 8501 for Streamlit or 8000 for API):
```powershell
docker build -t billie .
# For Streamlit UI
docker run -p 8501:8501 billie
# For API
docker run -p 8000:8000 billie
```

**How to interpret what you see**
- **`answer`**: the chatbot's response.
- **`sources`**: list of documents/filenames used to support the answer — check these to verify claims.
- **`used_llm`**: `false` means the system returned a retrieval-only answer; `true` means an LLM was used.
- **`validation.grounded`**: `true` means the answer was supported by retrieved evidence; `false` means validation failed or no supporting evidence was found.
- **`validation.issues`**: human-readable list of problems when grounded is `false` (e.g., "No supporting evidence was available for validation."). If you see "Needs Review" in the UI, treat the answer as unverified until you confirm the sources.

Screenshots: If you see the UI message "I couldn't find relevant text or visual evidence in the current knowledge base," try a different query or add more documents to the `knowledge/` folder.

**Common problems & fixes (Windows-specific)**
- Symptom: `Fatal error in launcher: Unable to create process using '...\\other_env\\.venv\\Scripts\\python.exe'` or commands like `pip`/`streamlit` fail.
  - Cause: a broken or different virtualenv was active when wrappers were created, or the `Scripts` wrappers point to a different Python installation.
  - Fix (fresh PowerShell session, run from project root):
```powershell
# close other shells, then in a new PowerShell
cd C:\Users\Vishal\Desktop\project
Remove-Item -Recurse -Force .venv      # remove broken env
py -3 -m venv .venv
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
1. Install Python 3.10+.
2. Open PowerShell and `cd` to the project.
3. Run the Streamlit flow (see above) and open http://localhost:8501.
4. Type a question; examine `sources` and `validation` details.

**Next steps I can do for you**
- Add a one-click PowerShell setup script to create the venv and start Streamlit.
- Create a short explainer email/tutorial you can send to coworkers.

If you want the one-click setup script, tell me whether you prefer PowerShell or a cross-platform `bash` script and I’ll add it.
