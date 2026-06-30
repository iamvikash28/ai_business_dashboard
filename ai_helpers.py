"""
ai_helpers.py
Wraps the Gemini API for three features:
  1. AI-generated executive summary
  2. Natural language Q&A (pre-aggregated-context approach)
  3. Automated recommendations

Design choice: instead of letting the LLM write arbitrary SQL against the
database (text-to-SQL), we pre-compute a set of safe aggregate tables and
pass the relevant ones as context. This avoids SQL-injection-style risk
from LLM-generated queries and keeps answers grounded in real numbers.
"""

import os
import json
import time
import streamlit as st
from google import genai
from google.genai import errors as genai_errors

import db

MODEL = "gemini-2.5-flash"  # fast + free-tier friendly, swap for "gemini-2.5-pro" for higher quality


def get_client() -> genai.Client:
    # Locally this comes from .env (loaded via python-dotenv in app.py).
    # On Streamlit Cloud, .env files aren't deployed -- the key must be
    # added under app Settings -> Secrets instead, which Streamlit exposes
    # via st.secrets. We check both so the same code works in either place.
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to your .env file locally, or "
            "to your app's Secrets if deployed on Streamlit Cloud."
        )
    return genai.Client(api_key=api_key)


def _generate_with_retry(client, max_retries: int = 3, **kwargs):
    """Calls client.models.generate_content with retry + backoff for
    transient errors (503 model overloaded, 429 rate limited). Raises a
    friendly RuntimeError if all retries are exhausted."""
    delay = 2  # seconds
    last_err = None
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(**kwargs)
        except genai_errors.ServerError as e:
            # 503 UNAVAILABLE and similar transient server-side errors
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
        except genai_errors.ClientError as e:
            # 429 rate limit can sometimes also be worth a brief retry
            if getattr(e, "code", None) == 429 and attempt < max_retries - 1:
                last_err = e
                time.sleep(delay)
                delay *= 2
            else:
                raise
    raise RuntimeError(
        "Gemini is currently busy (high demand) and didn't respond after "
        f"{max_retries} attempts. Please try again in a minute."
    ) from last_err


def _build_business_context() -> str:
    """Pulls key aggregates from SQL and formats them as compact text
    the LLM can reason over. This is the 'context' fed to every prompt."""

    kpis = db.total_kpis().iloc[0].to_dict()
    by_month = db.revenue_by_month().tail(6).to_dict(orient="records")
    by_product = db.revenue_by_product().to_dict(orient="records")
    by_region = db.revenue_by_region().to_dict(orient="records")

    # Compute simple MoM trend per product (last two months) for "losing revenue" questions
    pm = db.product_month_over_month()
    trend_lines = []
    for product, group in pm.groupby("product"):
        group = group.sort_values("year_month")
        if len(group) >= 2:
            last, prev = group.iloc[-1], group.iloc[-2]
            change = last["revenue"] - prev["revenue"]
            pct = (change / prev["revenue"] * 100) if prev["revenue"] else 0
            trend_lines.append(
                f"{product}: {prev['year_month']}={prev['revenue']:.0f} -> "
                f"{last['year_month']}={last['revenue']:.0f} ({pct:+.1f}%)"
            )

    context = f"""
COMPANY KPIs (all time):
{json.dumps(kpis, indent=2)}

REVENUE BY MONTH (last 6 months):
{json.dumps(by_month, indent=2)}

REVENUE BY PRODUCT (all time, sorted desc):
{json.dumps(by_product, indent=2)}

REVENUE BY REGION (all time):
{json.dumps(by_region, indent=2)}

PRODUCT MONTH-OVER-MONTH (last vs prior month):
{chr(10).join(trend_lines)}
""".strip()

    return context


def generate_executive_summary() -> str:
    context = _build_business_context()
    client = get_client()

    prompt = f"""You are a business analyst. Using ONLY the data below, write a concise
executive summary (4-6 sentences) of company performance. Mention overall
revenue/profit trend, any notable month-over-month changes, and the
strongest and weakest performing products or regions. Be specific with
numbers. Do not invent data not present below.

DATA:
{context}
"""
    resp = _generate_with_retry(
        client,
        model=MODEL,
        contents=prompt,
        config={"temperature": 0.3},
    )
    return resp.text


def generate_recommendations() -> str:
    context = _build_business_context()
    client = get_client()

    prompt = f"""You are a business consultant. Using ONLY the data below, give 3-5
specific, actionable recommendations for next quarter. Format as a
numbered list. Each recommendation should reference a specific number,
product, or region from the data to justify it. Do not invent data.

DATA:
{context}
"""
    resp = _generate_with_retry(
        client,
        model=MODEL,
        contents=prompt,
        config={"temperature": 0.4},
    )
    return resp.text


def answer_question(question: str, history: list | None = None) -> str:
    """Natural language Q&A grounded in pre-aggregated SQL context.

    `history` (if provided) is a list of dicts shaped like
    {"role": "user"|"assistant", "content": "..."} — the same shape the
    old OpenAI-based version used. We convert it to Gemini's expected
    {"role": "user"|"model", "parts": [...]} turn format here so callers
    (app.py) don't need to change.
    """
    context = _build_business_context()
    client = get_client()

    system_instruction = (
        "You are a business intelligence assistant embedded in a "
        "company dashboard. Answer the user's question using ONLY "
        "the data provided below. If the data doesn't contain the "
        "answer, say so clearly instead of guessing. Be concise, "
        "cite specific numbers, and use plain English suitable for "
        "a non-technical manager.\n\nDATA:\n" + context
    )

    contents = []
    if history:
        for turn in history:
            role = "model" if turn.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": turn.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": question}]})

    resp = _generate_with_retry(
        client,
        model=MODEL,
        contents=contents,
        config={"temperature": 0.3, "system_instruction": system_instruction},
    )
    return resp.text


if __name__ == "__main__":
    print(_build_business_context()[:1000])
