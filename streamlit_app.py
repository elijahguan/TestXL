import csv
import json
import os
from datetime import datetime, timezone

import streamlit as st
from google import genai

from prompts import ANALYZE_PROMPT

st.set_page_config(page_title="TestXL", page_icon="📚", layout="wide")

MODEL = "gemini-3.5-flash-lite"
USAGE_LOG_PATH = "usage_log.csv"
FEEDBACK_LOG_PATH = "feedback_log.csv"


def check_passcode() -> None:
    """Gate the app behind a shared passcode. Stops execution until entered correctly."""
    if st.session_state.get("passcode_ok"):
        return

    try:
        correct_passcode = st.secrets["BETAUSERS"]
    except (KeyError, FileNotFoundError):
        correct_passcode = os.environ.get("BETAUSERS")

    if not correct_passcode:
        st.error(
            "No BETAUSERS passcode configured. Add BETAUSERS to your "
            "Streamlit Cloud app secrets, or to a local .env file for testing."
        )
        st.stop()

    st.title("📚 TestXL")
    st.caption("Beta access — enter the passcode you were given to continue.")
    entered = st.text_input("Passcode", type="password")
    if st.button("Enter"):
        if entered == correct_passcode:
            st.session_state["passcode_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect passcode.")
    st.stop()


def get_client() -> genai.Client:
    """Load the API key from Streamlit secrets (cloud) or environment (local)."""
    api_key = None
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        st.error(
            "No Gemini API key found. Add GEMINI_API_KEY to your "
            "Streamlit Cloud app secrets, or to a local .env file for testing."
        )
        st.stop()
    return genai.Client(api_key=api_key)


def _append_csv_row(path: str, header: list[str], row: list) -> None:
    """Append a row to a local CSV, writing the header first if the file is new.
    Best-effort — logging must never break the app if it fails."""
    try:
        file_exists = os.path.exists(path)
        with open(path, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerow(row)
    except Exception:
        pass


def log_usage(response, language: str) -> None:
    usage = getattr(response, "usage_metadata", None)
    _append_csv_row(
        USAGE_LOG_PATH,
        ["timestamp_utc", "model", "language", "prompt_tokens", "output_tokens", "total_tokens"],
        [
            datetime.now(timezone.utc).isoformat(),
            MODEL,
            language,
            getattr(usage, "prompt_token_count", None) if usage else None,
            getattr(usage, "candidates_token_count", None) if usage else None,
            getattr(usage, "total_token_count", None) if usage else None,
        ],
    )


def log_feedback(question_preview: str, topic: str, rating: str, comment: str) -> None:
    _append_csv_row(
        FEEDBACK_LOG_PATH,
        ["timestamp_utc", "topic", "question_preview", "rating", "comment"],
        [datetime.now(timezone.utc).isoformat(), topic, question_preview, rating, comment],
    )


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            first_line, rest = cleaned.split("\n", 1)
            cleaned = rest if first_line.lower().startswith("json") else cleaned
    return cleaned.strip()


def analyze_questions(raw_text: str, language: str) -> dict:
    client = get_client()

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=ANALYZE_PROMPT.format(raw_text=raw_text, language=language),
        )
    except Exception as e:
        error_text = str(e).lower()
        if "429" in error_text or "rate limit" in error_text or "quota" in error_text or "resource_exhausted" in error_text:
            st.error(
                "We've hit the free-tier rate limit for the moment. "
                "Wait a minute or two and try again."
            )
        else:
            st.error(f"Something went wrong talking to the AI: {e}")
        st.stop()

    log_usage(response, language)

    response_text = response.text
    cleaned = _strip_code_fences(response_text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        st.error("Couldn't parse the AI's response as JSON. Raw output below for debugging:")
        st.code(response_text)
        st.stop()


# --- UI ---

check_passcode()

st.title("📚 TestXL")
st.caption(
    "Paste in your practice questions. TestXL sorts them by topic, generates a "
    "variant for each one to test real understanding, and flags concepts worth "
    "extra attention."
)

raw_text = st.text_area(
    "Paste your questions here (include answers if you have them):",
    height=280,
    placeholder=(
        "1. What is escrow?\n"
        "A) ...\nB) ...\nC) ...\n"
        "Correct answer: B\n\n"
        "2. ..."
    ),
)

language = st.selectbox("Answer language", ["English", "Chinese"])

col1, col2 = st.columns([1, 5])
with col1:
    analyze_clicked = st.button("Analyze", type="primary")
with col2:
    if "result" in st.session_state and st.button("Clear results"):
        del st.session_state["result"]
        st.rerun()

if analyze_clicked:
    if not raw_text.strip():
        st.warning("Paste in some questions first.")
    else:
        with st.spinner("Analyzing your questions..."):
            st.session_state["result"] = analyze_questions(raw_text, language)

if "result" in st.session_state:
    questions = st.session_state["result"].get("questions", [])

    topics: dict[str, list[tuple[int, dict]]] = {}
    for idx, q in enumerate(questions):
        topics.setdefault(q.get("topic", "Uncategorized"), []).append((idx, q))

    st.divider()
    st.subheader(f"{len(questions)} question(s) across {len(topics)} topic(s)")

    for topic, qs in topics.items():
        st.markdown(f"### {topic}")
        for idx, q in qs:
            flag_prefix = "⚠️ " if q.get("flagged") else ""
            preview = (q.get("original_question") or "")[:90]
            with st.expander(f"{flag_prefix}{preview}"):
                st.markdown(f"**Original question:** {q.get('original_question')}")
                if q.get("original_answer"):
                    st.markdown(f"**Answer:** {q.get('original_answer')}")
                st.markdown(f"**Explanation:** {q.get('explanation')}")
                if q.get("flagged"):
                    st.warning(f"Watch out: {q.get('flag_reason')}")

                st.markdown("---")

                show_key = f"show_variant_{idx}"
                if not st.session_state.get(show_key):
                    if st.button("🎯 Click this button to try a similar question", key=f"variant_btn_{idx}"):
                        st.session_state[show_key] = True
                        st.rerun()
                else:
                    choices = q.get("variant_choices", [])
                    correct_idx = q.get("variant_correct_index")

                    st.markdown(f"**{q.get('variant_question')}**")
                    selected = st.radio(
                        "Choose an answer:",
                        choices,
                        key=f"variant_choice_{idx}",
                        index=None,
                    )

                    if st.button("Submit answer", key=f"submit_variant_{idx}"):
                        if selected is None:
                            st.warning("Pick an answer first.")
                        else:
                            correct_choice = (
                                choices[correct_idx]
                                if correct_idx is not None and correct_idx < len(choices)
                                else None
                            )
                            if selected == correct_choice:
                                st.success("Correct!")
                            else:
                                st.error(f"Not quite — the correct answer was: {correct_choice}")
                            if q.get("variant_explanation"):
                                st.markdown(f"**Explanation:** {q.get('variant_explanation')}")

                st.markdown("---")

                feedback_key = f"feedback_given_{idx}"
                if not st.session_state.get(feedback_key):
                    st.markdown("**Was this question helpful?**")
                    fcol1, fcol2 = st.columns([1, 1])
                    with fcol1:
                        thumbs_up = st.button("👍 Helpful", key=f"thumbs_up_{idx}")
                    with fcol2:
                        thumbs_down = st.button("👎 Not helpful", key=f"thumbs_down_{idx}")
                    comment = st.text_input(
                        "Optional comment:", key=f"comment_{idx}", label_visibility="collapsed",
                        placeholder="Optional comment...",
                    )
                    if thumbs_up or thumbs_down:
                        log_feedback(
                            preview, topic, "up" if thumbs_up else "down", comment,
                        )
                        st.session_state[feedback_key] = True
                        st.rerun()
                else:
                    st.caption("Thanks for the feedback! 🙏")
