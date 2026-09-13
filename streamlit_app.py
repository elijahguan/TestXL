import json
import os

import streamlit as st
from google import genai

from prompts import ANALYZE_PROMPT

st.set_page_config(page_title="TestXL", page_icon="📚", layout="wide")

MODEL = "gemini-2.5-flash-lite"


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


def analyze_questions(raw_text: str) -> dict:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=ANALYZE_PROMPT.format(raw_text=raw_text),
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
            st.session_state["result"] = analyze_questions(raw_text)

if "result" in st.session_state:
    questions = st.session_state["result"].get("questions", [])

    topics: dict[str, list[dict]] = {}
    for q in questions:
        topics.setdefault(q.get("topic", "Uncategorized"), []).append(q)

    st.divider()
    st.subheader(f"{len(questions)} question(s) across {len(topics)} topic(s)")

    for topic, qs in topics.items():
        st.markdown(f"### {topic}")
        for q in qs:
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
                st.markdown(f"**Variant to try:** {q.get('variant_question')}")
                st.markdown(f"**Variant answer:** {q.get('variant_answer')}")
