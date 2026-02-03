# HW7-CareerCoach-AI-Project
AI Practitioner Crash Course 2026 - Homework 7
Build App  “ AI Travel Guide”
Asad Rizvi

travel_guide.py` uses a carefully engineered prompt to turn a large language model into a reliable travel-planning engine that reasons over user preferences and constraints to produce a structured, multi-day itinerary.

Inputs:
* Destination to Travel
* Number of Days
* Special Interests 
* Guardrails

Outputs:
* A complete day-by-day itinerary (Day 1..Day N)
* A Download PDF button
* Reset form + clear plan button (and “Clear fields only”)

---

## What the Code Does (Big Picture)

`travel_guide.py` is a **Travel Planning web app** built with **Streamlit** that uses an **AI language model (OpenAI GPT)** to generate a **day-by-day travel itinerary** based on user preferences and constraints, and then exports that plan as a **PDF**.

Think of it as:

> **A structured prompt + guardrails → AI reasoning → human-readable travel plan**

---

## Where AI Is Used (Core Idea)

The AI is responsible for **planning and reasoning**, not UI or formatting.

Specifically, the AI:

* Interprets user intent (destination, days, interests)
* Applies constraints (guardrails like accessibility or kid-friendly)
* Organizes activities logically across multiple days
* Produces structured, readable output (Markdown)

---

## AI-Related Components (Key Pieces)

### 1. Prompt Engineering (Most Important Part)

The code defines a **system prompt** that turns the AI into a:

> *“Practical Travel Planner that must obey guardrails strictly”*

This prompt:

* Forces a **specific output structure** (sections, days, bullets)
* Enforces **safety and constraint compliance**
* Prevents vague or rambling responses
* Makes output predictable and reusable (for PDF + UI)

This is classic **prompt-as-program** design.

---

### 2. User Input → AI Input Transformation

User form inputs are **not sent raw** to the model.

Instead, the code:

* Normalizes inputs (destination, days, interests, guardrails)
* Embeds them into a **structured user prompt**
* Adds instructions like:

  * Balance activities across days
  * Prioritize guardrails over interests
  * Avoid repeating activities

This is an example of **controlled natural-language programming**.

---

### 3. AI Model Invocation (Reasoning Step)

The AI call:

* Uses GPT models (`gpt-5`, `gpt-5-mini`, fallback to `gpt-4.1`)
* Requests a bounded response size
* Treats the AI as a **planner**, not a chatbot

Key idea:

> The AI is doing **multi-day planning, constraint satisfaction, and content generation** in one step.

This is **reasoning over time**, not just text completion.

---

### 4. Model Fallback Strategy (Production Pattern)

The code doesn’t rely on a single model.

Instead:

* Tries a primary model
* Falls back to others if needed
* Ensures the app still works even if one model fails

This is a **production-grade AI reliability pattern**.

---

### 5. Structured Output Parsing (AI → App)

The AI is instructed to output **Markdown**.

Why this matters:

* Markdown is both **human-readable** and **machine-friendly**
* The same AI output is reused for:

  * On-screen display
  * PDF generation

This avoids re-prompting or post-processing the AI.

---

## What the AI Is *Not* Doing

The AI does **not**:

* Handle UI logic
* Generate PDFs directly
* Store user data
* Access the internet or live travel APIs
* Make bookings or pricing decisions

All of that is intentionally handled **outside** the AI.

---

## Mental Model (How to Think About This App)

You can think of the AI as:

> **A constrained reasoning engine that converts preferences + rules into a structured plan**

```
User Preferences + Guardrails
            ↓
   Structured Prompt (Rules)
            ↓
      AI Reasoning Engine
            ↓
   Predictable Markdown Output
            ↓
     UI display + PDF export
```
## How to Run travel_guide.py (Simple)

Install Python (3.9 or newer)

Install required packages

pip install streamlit openai python-dotenv reportlab


Set your OpenAI API key

Either put this in a .env file:

OPENAI_API_KEY=your_key_here


Or set it as an environment variable

Run the app

streamlit run travel_guide.py


Open the browser link Streamlit shows (usually http://localhost:8501)
