import json
import os

import streamlit as st
from google import genai

from prompts import ANALYZE_PROMPT

st.set_page_config(page_title="TestXL", page_icon="📚", layout="wide")

MODEL = "gemini-3.5-flash-lite"


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
    response = client.models.generate_content(
        model=MODEL,
        contents=ANALYZE_PROMPT.format(raw_text=raw_text, language=language),
    )
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
