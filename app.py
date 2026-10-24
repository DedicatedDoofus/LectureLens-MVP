"""LectureLens: an AI instructional-coaching MVP for online lectures.

Run with:
    streamlit run app.py

The app uses Google's Gemini Interactions API when GEMINI_API_KEY is available.
If the key is missing, it switches to a clearly labeled local demo mode so the
UI can still be demonstrated in class.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional convenience dependency
    pass

try:
    from google import genai
except ImportError:  # pragma: no cover - the requirements file installs it
    genai = None  # type: ignore[assignment]


APP_NAME = "LectureLens"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

SAMPLE_TRANSCRIPT = """[00:00] Instructor: Today we are going to review Java arrays and how indexing works.
[00:18] Instructor: Give me one second while I share the correct screen. I opened the wrong window.
[00:52] Instructor: Okay, arrays store multiple values of the same type. For example, int[] scores = {80, 90, 75}.
[01:34] Instructor: The first item is at index zero. Does that make sense?
[01:48] Student: I think so, but I am not sure why the first index is not one.
[02:02] Instructor: Right, computers count offsets from zero. So scores[0] gives us 80.
[02:26] Instructor: What do you think scores[1] will return?
[02:39] Student: 90.
[02:44] Instructor: Exactly. Now change the example so that it stores four scores.
[03:10] Student: I am trying, but I am getting an error.
[03:22] Instructor: Let us look at it together. You used scores[4], but the valid indexes stop at 3.
[04:06] Instructor: Any questions before we move on? ... Okay, let us continue with the for loop.
[04:38] Instructor: A for loop is useful when we want to visit every element in the array.
[05:15] Instructor: Does that make sense? Great. I will show the completed code now.
"""


SYSTEM_PROMPT = """You are LectureLens, an evidence-based instructional coach for one-on-one and
small-group online programming lectures.

Your job is to turn a timestamped lecture transcript into specific, respectful,
and practical coaching. Use only observable evidence in the transcript. Do not
claim that you can directly measure a student's thoughts, attention, motivation,
or emotions. Instead, describe observable proxies such as long pauses, explicit
uncertainty, unanswered questions, or successful responses.

Prompt pattern 1 - Persona and constraints:
- Act like a supportive teaching coach, not a grader.
- Separate evidence from interpretation.
- Give one small action the instructor can try in the next lesson.
- Make recommendations concrete enough to be demonstrated live.

Prompt pattern 2 - Few-shot example:
Transcript: "[02:10] Instructor: Does that make sense? [02:25] Student: ..."
Good recommendation: cite 02:10-02:25, explain that a general check-in did not
produce observable confirmation, and suggest a low-pressure retrieval question
such as "What would this variable contain after the next line?"

Prompt pattern 3 - Iterative refinement:
First identify evidence and possible teaching opportunities. Then refine the
recommendations by removing unsupported claims, prioritizing the two or three
highest-value actions, and checking that every recommendation includes a
timestamp, evidence, impact, action, example prompt, and confidence level.

Return only the requested structured object. Do not include hidden reasoning or
an unstructured preamble.
"""


ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "scores": {
            "type": "object",
            "properties": {
                "engagement": {"type": "integer"},
                "questioning": {"type": "integer"},
                "clarity": {"type": "integer"},
                "participation": {"type": "integer"},
            },
            "required": ["engagement", "questioning", "clarity", "participation"],
            "additionalProperties": False,
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["Engagement", "Questioning", "Clarity", "Participation"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                    },
                    "timestamp": {"type": "string"},
                    "evidence": {"type": "string"},
                    "impact": {"type": "string"},
                    "action": {"type": "string"},
                    "example_prompt": {"type": "string"},
                    "confidence": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low"],
                    },
                },
                "required": [
                    "category",
                    "priority",
                    "timestamp",
                    "evidence",
                    "impact",
                    "action",
                    "example_prompt",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
        "next_lesson_plan": {"type": "array", "items": {"type": "string"}},
        "attention_note": {"type": "string"},
    },
    "required": [
        "title",
        "summary",
        "scores",
        "strengths",
        "recommendations",
        "next_lesson_plan",
        "attention_note",
    ],
    "additionalProperties": False,
}


def demo_analysis(transcript: str, focus: str) -> dict[str, Any]:
    """Create a deterministic, clearly labeled fallback for a live demo."""

    question_count = transcript.count("?")
    uncertainty = bool(re.search(r"not sure|getting an error|confused|unclear", transcript, re.I))
    vague_checkin = bool(re.search(r"does that make sense|any questions", transcript, re.I))
    setup_delay = bool(re.search(r"one second|wrong window|share the correct screen", transcript, re.I))

    scores = {
        "engagement": min(96, 69 + question_count * 3),
        "questioning": min(96, 61 + question_count * 5),
        "clarity": 78 if not uncertainty else 73,
        "participation": 70 if uncertainty else 77,
    }

    recommendations: list[dict[str, str]] = []
    if setup_delay:
        recommendations.append(
            {
                "category": "Engagement",
                "priority": "Medium",
                "timestamp": "00:18-00:52",
                "evidence": "The instructor pauses to find the correct screen before the lesson content begins.",
                "impact": "A planned opening task could keep the learner active during setup time.",
                "action": "Prepare the code window before class and place a one-minute prediction question on screen as a backup.",
                "example_prompt": "Before I share the solution, predict what the first array index will be.",
                "confidence": "High",
            }
        )
    if vague_checkin:
        recommendations.append(
            {
                "category": "Questioning",
                "priority": "High",
                "timestamp": "01:34 and 05:15",
                "evidence": "The instructor uses broad checks such as ‘Does that make sense?’ without always requesting a visible response.",
                "impact": "A learner can agree politely without demonstrating whether the concept is usable.",
                "action": "Replace one broad check-in with a short retrieval or prediction question.",
                "example_prompt": "What value will scores[1] contain, and why?",
                "confidence": "High",
            }
        )
    if uncertainty:
        recommendations.append(
            {
                "category": "Clarity",
                "priority": "High",
                "timestamp": "01:48 and 03:10-03:22",
                "evidence": "The student says they are unsure about zero-based indexing and later reports an error.",
                "impact": "These are useful moments to slow down, surface the mental model, and check the next step.",
                "action": "Ask the learner to trace one concrete example before returning to the abstract rule.",
                "example_prompt": "Point to the three values and tell me the valid indexes from left to right.",
                "confidence": "High",
            }
        )
    recommendations.append(
        {
            "category": "Participation",
            "priority": "Medium",
            "timestamp": "02:44-03:10",
            "evidence": "The instructor gives the learner a small code change to make, creating an observable opportunity to participate.",
            "impact": "Short learner actions provide stronger evidence of understanding than extended instructor explanation alone.",
            "action": "Keep the task, but add a quick explanation request after the learner completes it.",
            "example_prompt": "What changed in the valid index range after adding the fourth score?",
            "confidence": "Medium",
        }
    )

    if focus != "All areas":
        focus_recommendations = [item for item in recommendations if item["category"] == focus]
        if focus_recommendations:
            recommendations = focus_recommendations + [
                item for item in recommendations if item["category"] != focus
            ]

    return {
        "title": "Java arrays: engagement and understanding check",
        "summary": "The lesson contains useful guided practice and one successful prediction question. The biggest opportunity is replacing broad check-ins with short, observable responses and using student uncertainty as a cue to trace one concrete example.",
        "scores": scores,
        "strengths": [
            "The instructor connects the zero-based-index rule to a concrete array.",
            "The learner is invited to predict a value and then modify the code.",
            "The instructor responds constructively when an indexing error appears.",
        ],
        "recommendations": recommendations,
        "next_lesson_plan": [
            "Prepare the code window and a backup prediction task before the call.",
            "Replace at least two broad check-ins with retrieval questions.",
            "After each learner action, ask for a one-sentence explanation of the result.",
        ],
        "attention_note": "LectureLens does not measure attention or internal mental states. These observations are based only on visible transcript signals such as questions, pauses, uncertainty, and completed responses.",
    }


def call_gemini(transcript: str, focus: str) -> dict[str, Any]:
    """Ask Gemini for structured coaching output."""

    if genai is None:
        raise RuntimeError("The google-genai package is not installed.")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    user_prompt = f"""Analyze this online lecture transcript.

Analysis focus: {focus}

Return a balanced analysis, but prioritize recommendations related to the focus.
Keep the output concise enough for a dashboard. Use exact timestamps when they
appear in the transcript. If a conclusion is uncertain, lower the confidence
instead of inventing evidence.

TRANSCRIPT
-----------
{transcript}
"""

    interaction = client.interactions.create(
        model=DEFAULT_MODEL,
        system_instruction=SYSTEM_PROMPT,
        input=user_prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ANALYSIS_SCHEMA,
        },
        store=False,
    )

    if not interaction.output_text:
        raise RuntimeError("The model returned an empty response.")
    return json.loads(interaction.output_text)


def render_score(label: str, value: int, column: Any) -> None:
    with column:
        st.metric(label, f"{value}/100")
        st.progress(max(0, min(100, value)) / 100)


def render_recommendation(item: dict[str, str], index: int) -> None:
    category_icons = {
        "Engagement": "⚡",
        "Questioning": "❓",
        "Clarity": "🔎",
        "Participation": "🙋",
    }
    icon = category_icons.get(item.get("category", ""), "💡")
    st.markdown(f"**{icon} {item.get('category', 'Recommendation')}**  ·  {item.get('priority', 'Medium')} priority  ·  `{item.get('timestamp', 'n/a')}`")
    st.write(item.get("action", ""))
    evidence_col, impact_col = st.columns(2)
    with evidence_col:
        st.caption("Evidence")
        st.write(item.get("evidence", ""))
    with impact_col:
        st.caption("Why it matters")
        st.write(item.get("impact", ""))
    st.info(f"Try asking: {item.get('example_prompt', '')}  ·  Confidence: {item.get('confidence', 'Medium')}")
    if index < 99:
        st.divider()


st.set_page_config(page_title=APP_NAME, page_icon="🎓", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
    .hero { padding: 1.6rem 1.8rem; border-radius: 20px; background: linear-gradient(135deg, #172554 0%, #312e81 55%, #0f766e 100%); color: white; margin-bottom: 1.2rem; }
    .hero h1 { margin: 0; font-size: 2.4rem; letter-spacing: -0.04em; }
    .hero p { margin: .45rem 0 0; color: #dbeafe; font-size: 1.05rem; }
    .small-note { color: #64748b; font-size: .88rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("🎓 LectureLens")
    st.caption("AI instructional coaching for online lectures")
    st.divider()
    focus = st.selectbox(
        "Analysis focus",
        ["All areas", "Engagement", "Questioning", "Clarity", "Participation"],
    )
    use_ai = st.checkbox("Use Gemini when available", value=True)
    if os.getenv("GEMINI_API_KEY") and use_ai:
        st.success(f"Gemini mode ready · {DEFAULT_MODEL}")
    else:
        st.info("Demo mode is ready. Add GEMINI_API_KEY to enable live model analysis.")
    st.divider()
    with st.expander("Prompt engineering used"):
        st.markdown(
            "**Persona + constraints:** supportive instructional coach; evidence only; no claims about internal attention.\n\n"
            "**Few-shot example:** demonstrates how a vague check-in becomes a specific retrieval question.\n\n"
            "**Iterative refinement:** identify evidence, prioritize actions, then check timestamps, confidence, and unsupported claims."
        )

st.markdown(
    '<div class="hero"><h1>LectureLens</h1><p>Turn a lecture transcript into evidence-based coaching that an instructor can use in the next class.</p></div>',
    unsafe_allow_html=True,
)

input_col, setup_col = st.columns([1.4, 0.8])
with input_col:
    st.subheader("1. Add lecture evidence")
    source = st.radio(
        "Choose an input",
        ["Built-in sample", "Paste transcript", "Upload .txt"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if source == "Built-in sample":
        transcript = SAMPLE_TRANSCRIPT
        st.caption("Synthetic Java lecture sample for a reliable presentation demo.")
    elif source == "Paste transcript":
        transcript = st.text_area(
            "Paste a timestamped transcript",
            value=st.session_state.get("transcript", ""),
            height=300,
            placeholder="[00:00] Instructor: ...\n[00:15] Student: ...",
        )
        st.session_state["transcript"] = transcript
    else:
        uploaded = st.file_uploader("Upload a plain-text transcript", type=["txt"])
        transcript = uploaded.read().decode("utf-8", errors="replace") if uploaded else ""
        if transcript:
            st.text_area("Uploaded transcript preview", transcript, height=220)

with setup_col:
    st.subheader("2. Run the coach")
    st.write("LectureLens looks for observable evidence of explanation, questioning, learner participation, and moments where a teacher can check understanding.")
    analyze = st.button("Analyze lecture", type="primary", use_container_width=True)
    st.caption("Tip: use the built-in sample first for the live presentation.")

if analyze:
    if len(transcript.strip()) < 40:
        st.warning("Add a little more transcript text before analyzing.")
    else:
        with st.spinner("Reviewing evidence and refining recommendations..."):
            if use_ai and os.getenv("GEMINI_API_KEY"):
                try:
                    result = call_gemini(transcript, focus)
                    source_label = f"Live Gemini analysis · {DEFAULT_MODEL}"
                    error_message = ""
                except Exception as exc:  # demo fallback keeps the presentation usable
                    result = demo_analysis(transcript, focus)
                    source_label = "Local demo fallback"
                    error_message = str(exc)
            else:
                result = demo_analysis(transcript, focus)
                source_label = "Local demo mode"
                error_message = ""
        st.session_state["analysis"] = result
        st.session_state["source_label"] = source_label
        st.session_state["error_message"] = error_message

analysis = st.session_state.get("analysis")
if analysis:
    st.divider()
    source_label = st.session_state.get("source_label", "Analysis")
    error_message = st.session_state.get("error_message", "")
    st.success(source_label)
    if error_message:
        st.caption(f"The API was unavailable, so the deterministic presentation fallback was used: {error_message}")

    st.header(analysis.get("title", "Lecture analysis"))
    st.write(analysis.get("summary", ""))

    scores = analysis.get("scores", {})
    score_cols = st.columns(4)
    render_score("Engagement", int(scores.get("engagement", 0)), score_cols[0])
    render_score("Questioning", int(scores.get("questioning", 0)), score_cols[1])
    render_score("Clarity", int(scores.get("clarity", 0)), score_cols[2])
    render_score("Participation", int(scores.get("participation", 0)), score_cols[3])

    strength_col, note_col = st.columns([1, 1])
    with strength_col:
        st.subheader("What is working")
        for strength in analysis.get("strengths", []):
            st.markdown(f"✅ {strength}")
    with note_col:
        st.subheader("Responsible interpretation")
        st.info(analysis.get("attention_note", "Use observable evidence only."))

    st.subheader("Actionable recommendations")
    recommendations = analysis.get("recommendations", [])
    visible = [item for item in recommendations if focus == "All areas" or item.get("category") == focus]
    if not visible:
        visible = recommendations
    for index, item in enumerate(visible):
        render_recommendation(item, index)

    st.subheader("Next-lesson action plan")
    for number, item in enumerate(analysis.get("next_lesson_plan", []), start=1):
        st.markdown(f"**{number}.** {item}")

    with st.expander("Show the prompt-engineering design used by this MVP"):
        st.markdown(
            "**Persona pattern:** The system prompt establishes LectureLens as a supportive instructional coach and limits it to observable evidence.\n\n"
            "**Few-shot pattern:** A transcript snippet with a vague ‘Does that make sense?’ check is paired with a concrete retrieval-question recommendation.\n\n"
            "**Iterative-refinement pattern:** The prompt directs the model to identify evidence first, refine unsupported conclusions, prioritize actions, and validate the required fields.\n\n"
            "**Structured output:** The Gemini response is constrained to a JSON schema so the UI can reliably render scores, evidence, recommendations, confidence, and a next-lesson plan."
        )

st.markdown(
    '<p class="small-note">LectureLens is a coaching aid, not a surveillance tool. It should support instructor reflection and should not be used to label a student’s internal attention or ability.</p>',
    unsafe_allow_html=True,
)
