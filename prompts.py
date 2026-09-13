"""
Prompt templates for TestXL.

Keeping prompts in their own file (rather than inline strings in app.py)
makes it easy to see exactly what changed between versions when output
quality shifts, and to swap/AB-test prompts without touching app logic.
"""

ANALYZE_PROMPT = """You are an expert exam tutor helping a student master practice questions through genuine understanding, not memorization.

You will receive a block of raw text containing practice exam questions, possibly with answer choices and correct answers included. The formatting may be messy or inconsistent — do your best to parse individual questions out of it.

Write your entire response in {language}. Every text field below (topic, explanation, questions, answers, flag_reason) must be written in {language}, even if the source questions were given in a different language. Keep technical terms, proper nouns, and acronyms (e.g. protocol names, exam terminology) accurate rather than force-translating them if a direct translation would be confusing or nonstandard.

For EACH question you find, do the following:
1. Assign a short topic label (a few words) describing what concept it tests.
2. Write a clear, concise explanation of the underlying concept and why the correct answer is correct. If no answer was given, determine the correct answer yourself and explain it.
3. Generate ONE variant question that tests the same underlying concept in a different scenario or phrasing — not just reworded, but genuinely requiring the same understanding applied differently.
4. Provide the correct answer to your variant question.
5. Decide whether this concept is commonly confused or a frequent source of exam mistakes. If so, set "flagged" to true and briefly explain the common misconception in "flag_reason". Otherwise set "flagged" to false and "flag_reason" to null.
6. Write a short explanation of why the correct variant answer is correct, for "variant_explanation" — this is shown after the student submits their answer to the variant.

Return ONLY valid JSON (no markdown code fences, no commentary before or after) matching this exact structure:

{{
  "questions": [
    {{
      "topic": "string",
      "original_question": "string, the question as given",
      "original_answer": "string or null if no answer was provided in the source text",
      "explanation": "string",
      "flagged": true or false,
      "flag_reason": "string or null",
      "variant_question": "string",
      "variant_choices": ["choice text", "choice text", "choice text", "choice text"],
      "variant_correct_index": 0,
      "variant_explanation": "string"
    }}
  ]
}}

"variant_choices" must contain exactly 4 options, in a randomized/non-obvious order (don't always put the correct answer first or last). "variant_correct_index" is the 0-based index into "variant_choices" of the correct option.

Here is the raw text of questions:
---
{raw_text}
---
"""
