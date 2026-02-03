# travel_guide.py
# -----------------------------------------------
# Travel Guide (Streamlit + OpenAI)
# - Collects trip inputs (destination, days, interests, guardrails)
# - Calls GPT models with robust fallbacks
# - Renders a day-by-day itinerary on-screen
# - Generates a clean PDF (0.5" left/right margins)
# -----------------------------------------------

import os
from datetime import datetime
from textwrap import dedent

import streamlit as st               # ✅ REQUIRED
from dotenv import load_dotenv       # ✅ REQUIRED
from openai import OpenAI            # ✅ REQUIRED

# PDF generation (install: pip install reportlab)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
)

try:
    import streamlit
    import openai
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
except ImportError as e:
    raise SystemExit(
        "\n❌ Missing dependency.\n"
        "Run:\n"
        "  pip install -r requirements.txt\n\n"
        f"Details: {e}\n"
    )

# -------------------------
# ENV & CLIENT
# -------------------------
load_dotenv()  # reads .env if present
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------
# STREAMLIT CONFIG
# -------------------------
st.set_page_config(
    page_title="Travel Guide",
    page_icon="🧳",
    layout="centered",
)

FORM_KEYS = [
    "destination",
    "num_days",
    "interests",
    "guardrails",
]

def init_form_state():
    st.session_state.setdefault("destination", "")
    st.session_state.setdefault("num_days", 3)
    st.session_state.setdefault("interests", "")
    st.session_state.setdefault("guardrails", "")
    st.session_state.setdefault("plan_md", "")

def reset_all_callback():
    st.session_state["destination"] = ""
    st.session_state["num_days"] = 3
    st.session_state["interests"] = ""
    st.session_state["guardrails"] = ""
    st.session_state["plan_md"] = ""
    st.session_state.pop("last_model_used", None)
    st.session_state.pop("last_usage", None)

def clear_fields_only_callback():
    st.session_state["destination"] = ""
    st.session_state["num_days"] = 3
    st.session_state["interests"] = ""
    st.session_state["guardrails"] = ""

init_form_state()

# -------------------------
# UI HEADER
# -------------------------
st.title("🧳 Travel Guide")
st.caption("Streamlit + OpenAI demo: generates a day-by-day travel plan and a downloadable PDF.")

with st.expander("What this app does", expanded=False):
    st.markdown(
        "- Takes your **destination**, **number of days**, **interests**, and **guardrails**\n"
        "- Generates a **complete day-by-day itinerary**\n"
        "- Lets you **download a PDF** version"
    )

# -------------------------
# PROMPTS
# -------------------------
SYSTEM_PROMPT = dedent("""
You are a practical TRAVEL PLANNER.
You must obey any guardrails (constraints) strictly.

Output rules:
- Output in Markdown.
- Use these top-level H2 sections (##):
  ## Trip Overview
  ## Day-by-Day Plan
  ## Practical Notes
- Inside '## Day-by-Day Plan', provide:
  - Day 1, Day 2, ... Day N as H3 headings (### Day X)
  - For each day, include Morning / Afternoon / Evening
  - 4-8 bullet items total per day (across sections), not walls of text
- Keep suggestions realistic and geographically coherent (cluster activities by area).
- If the user says "no walking tours", avoid heavy walking routes.
- If the user says kids-friendly or wheelchair accessible, ensure the plan respects that.
- Include food suggestions if interest includes food & cuisine.
- Include at least one low-energy option per day (e.g., café, scenic view, market).
- Avoid unsafe or illegal activities. Avoid medical advice.

If destination is ambiguous, assume the most common city/country match and note the assumption in Trip Overview.
""").strip()

def build_user_prompt(destination: str, num_days: int, interests: str, guardrails: str) -> str:
    return dedent(f"""
    TRIP INPUTS
    - Destination: {destination or 'N/A'}
    - Number of days: {num_days}
    - Special interests: {interests or 'None'}
    - Guardrails / constraints: {guardrails or 'None'}

    INSTRUCTIONS
    - Generate a complete plan for {num_days} days (Day 1..Day {num_days}).
    - Balance interests across days; do not repeat the exact same type of activity back-to-back unless necessary.
    - Use bullet points for activities with short labels and 1-line details.
    - Include suggested "time windows" (e.g., 9–12) optionally, but keep it readable.
    - If guardrails conflict with interests, prioritize guardrails and explain briefly in Practical Notes.
    """).strip()

# -------------------------
# FALLBACKS & EXTRACTOR
# -------------------------
FALLBACK_MODELS = ["gpt-5", "gpt-5-mini", "gpt-4.1"]  # try in order

def _extract_text_from_chat_completion(comp) -> str:
    """
    Defensive extractor for minor SDK/shape changes.
    """
    try:
        txt = comp.choices[0].message.content
        if isinstance(txt, str) and txt.strip():
            return txt
        if isinstance(txt, list):
            parts = []
            for p in txt:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict) and isinstance(p.get("text"), str):
                    parts.append(p["text"])
            joined = "\n".join(parts).strip()
            if joined:
                return joined
    except Exception:
        pass
    return ""

def get_plan_markdown(user_prompt: str) -> str:
    """
    Robust call with model fallbacks and modern parameters.
    - Uses max_completion_tokens (not max_tokens)
    - Omits temperature/top_p for GPT-5/4.1 variants
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            comp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_completion_tokens=2200,
            )
            text = _extract_text_from_chat_completion(comp)
            if text.strip():
                st.session_state["last_model_used"] = model_name
                st.session_state["last_usage"] = getattr(comp, "usage", None)
                return text
            last_error = RuntimeError(f"Model '{model_name}' returned empty content.")
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All model attempts failed. Last error: {last_error}")

# -------------------------
# PDF HELPERS
# -------------------------
def markdown_to_flowables(md_text: str, styles):
    """
    Lightweight Markdown -> ReportLab flowables:
    - '## ' -> Heading2
    - '### ' -> Heading3
    - Bullets '-', '*', '•' -> unordered lists
    - Otherwise -> paragraph
    """
    flow = []
    body = styles["BodyText"]
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            flow.append(Spacer(1, 6))
            i += 1
            continue

        if line.startswith("## "):
            flow.append(Paragraph(line[3:].strip(), h2))
            i += 1
            continue
        if line.startswith("### "):
            flow.append(Paragraph(line[4:].strip(), h3))
            i += 1
            continue

        if line.lstrip().startswith(("-", "*", "•")):
            items = []
            while i < len(lines) and lines[i].lstrip().startswith(("-", "*", "•")):
                bullet_text = lines[i].lstrip()[1:].strip()
                items.append(ListItem(Paragraph(bullet_text, body), leftIndent=12))
                i += 1
            flow.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=6))
            flow.append(Spacer(1, 4))
            continue

        flow.append(Paragraph(line, body))
        i += 1

    return flow

def write_pdf(markdown_text: str, filename: str = "travel_plan.pdf") -> str:
    # Letter with 0.5" left/right margins (and ~0.7" top/bottom)
    doc = SimpleDocTemplate(
        filename,
        pagesize=LETTER,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Travel Plan",
        author="Travel Guide",
    )
    styles = getSampleStyleSheet()

    header = ParagraphStyle(
        "Header",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )

    story = []
    story.append(Paragraph("Travel Plan", header))
    meta = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    story.append(Paragraph(meta, styles["Normal"]))
    story.append(Spacer(1, 10))

    story.extend(markdown_to_flowables(markdown_text, styles))
    doc.build(story)
    return filename

# -------------------------
# INPUT FORM
# -------------------------
with st.form("travel_inputs"):
    st.text_input(
        "1) Destination to Travel",
        placeholder="e.g., Tokyo, Japan",
        key="destination",
    )

    st.number_input(
        "2) Number of Days",
        min_value=1,
        max_value=30,
        step=1,
        key="num_days",
        help="Keep it between 1 and 30 for best results.",
    )

    st.text_area(
        "3) Special Interests",
        placeholder="e.g., Museums, Food & Cuisine, Historic sites, Nature",
        key="interests",
        help="Comma-separated is fine.",
    )

    st.text_area(
        "4) Guardrails / Constraints",
        placeholder="e.g., No walking tours; only kids-friendly activities; only wheelchair accessible places",
        key="guardrails",
    )

    submitted = st.form_submit_button("Generate Travel Plan")

# -------------------------
# QUICK API SELF-TEST
# -------------------------
with st.expander("Diagnostics (optional)", expanded=False):
    if st.button("Run quick API self-test"):
        try:
            ping = client.chat.completions.create(
                model=FALLBACK_MODELS[0],
                messages=[{"role": "user", "content": "Reply with the single word: READY"}],
                max_completion_tokens=10,
            )
            st.success("Self-test response:")
            st.code(_extract_text_from_chat_completion(ping))
        except Exception as e:
            st.error(f"Self-test failed: {e}")

# -------------------------
# MAIN ACTION
# -------------------------
if submitted:
    destination = (st.session_state["destination"] or "").strip()
    num_days = int(st.session_state["num_days"] or 0)

    if not destination:
        st.warning("Please provide a **Destination**.")
    elif num_days < 1:
        st.warning("Please provide a valid **Number of Days**.")
    else:
        with st.spinner("Generating your travel plan..."):
            user_prompt = build_user_prompt(
                destination=destination,
                num_days=num_days,
                interests=st.session_state["interests"],
                guardrails=st.session_state["guardrails"],
            )
            try:
                st.session_state["plan_md"] = get_plan_markdown(user_prompt)
            except Exception as e:
                st.error(f"Generation error: {e}")
                st.session_state["plan_md"] = ""

    if st.session_state["plan_md"].strip():
        st.success("Travel plan generated!")
        st.caption(f"Model: {st.session_state.get('last_model_used', 'unknown')}")
        if st.session_state.get("last_usage"):
            st.caption(f"Usage: {st.session_state['last_usage']}")

        st.subheader("Your Travel Plan")
        st.markdown(st.session_state["plan_md"], unsafe_allow_html=False)

        with st.expander("Show raw text (copy-friendly)"):
            st.text_area("Plan (raw)", st.session_state["plan_md"], height=420)

        # PDF export
        try:
            pdf_path = write_pdf(st.session_state["plan_md"], filename="travel_plan.pdf")
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=f.read(),
                    file_name="travel_plan.pdf",
                    mime="application/pdf",
                )
        except Exception as e:
            st.error(f"PDF generation error: {e}")
            st.info("You can still copy the plan above while we sort out PDF export.")
    else:
        st.warning("The model returned an empty response.")
        st.info("Try again, or verify your API key/model access in Diagnostics above.")
else:
    if "plan_md" in st.session_state and st.session_state["plan_md"].strip():
        st.subheader("Last Generated Plan")
        st.markdown(st.session_state["plan_md"], unsafe_allow_html=False)
    else:
        st.info("Fill in the fields above and click **Generate Travel Plan**.")

st.divider()
col_a, col_b = st.columns([1, 1])
with col_a:
    st.button("🔁 Reset form + clear plan", type="secondary", on_click=reset_all_callback)
with col_b:
    st.button("🧹 Clear fields only", type="secondary", on_click=clear_fields_only_callback)
