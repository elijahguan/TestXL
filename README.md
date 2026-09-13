# TestXL

Paste in practice exam questions. TestXL sorts them by topic, generates a
variant question for each one to test real understanding (not just recall),
and flags concepts worth extra attention.

## Why it's built this way

- **BYO-content first**: users paste in their own notes/practice questions
  rather than the tool shipping any pre-built question bank. This avoids
  reproducing anyone else's copyrighted exam content (e.g. Aceable's), and
  keeps the door open to an "objective-mapped generation" mode later that
  builds questions from official exam blueprints instead.
- **Single-file MVP on purpose**: no auth, no database, no billing. The goal
  right now is to find out whether the core mechanic (sort → generate variant
  → explain → flag) actually helps someone study better — not to build
  infrastructure for users we don't have yet.
- **Prompts live in `prompts.py`**, separate from app logic, so changes to
  prompt wording are easy to track and iterate on independently of the UI.

## Local setup

1. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your real Gemini API key
   (get one at https://aistudio.google.com/apikey):
   ```
   cp .env.example .env
   ```
3. Run the app:
   ```
   streamlit run streamlit_app.py
   ```

## Deploying to Streamlit Cloud (testxl.streamlit.app)

Streamlit Cloud does **not** read your local `.env` file — secrets are set
separately in the dashboard:

1. Push `streamlit_app.py`, `prompts.py`, and `requirements.txt` to the
   GitHub repo connected to your Streamlit Cloud app (root of the repo,
   matching the existing `streamlit_app.py` entry point).
2. In the Streamlit Cloud dashboard, open your app → **Settings → Secrets**.
3. Add:
   ```toml
   GEMINI_API_KEY = "your-api-key-here"
   ```
4. Save — the app will restart automatically and pick up the key.

## What's intentionally not built yet

- User accounts / login (fine for a single tester using a shared link)
- Saved history between sessions
- Cost tracking on API usage (worth adding once you're past one tester)
- Objective-mapped generation mode (BYO-content only for now)
