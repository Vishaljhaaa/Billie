# How a normal user would use the chatbot (Frontend guide)

This file explains how a typical end-user would interact with the chatbot and how to expose the backend to a frontend.

1. Deploy the FastAPI backend (locally or on a server) using `uvicorn` or Docker.

2. Protect the API with `X-API-Key` or run without auth for internal demos.

3. Frontend flow (basic):
  - User types a question and optionally uploads an image.
  - Frontend sends a `POST /chat` request with JSON body:
```json
{
  "question": "How does it update?",
  "session_id": "user-session-id",
  "image_inputs": [{"path": "uploads/abcd.png", "description": "screenshot"}]
}
```
  - Backend returns `ChatResponse` (answer, sources, evidence, etc.) and frontend displays the answer along with provenance and optional 'Details' panel.

4. For a Streamlit-based demo, use `streamlit_app.py` which provides a simple chat UI and file-upload widget.

UX suggestions
- Show provenance (source file/path) so users can trust answers.
- Display 'validation' status and a 'View Evidence' panel that shows matched snippets and images.
- Add a feedback button to let users mark answers as helpful; persist this for future evaluation.
