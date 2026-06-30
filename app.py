"""
app.py
AI Business Insights Dashboard - Streamlit entry point.

Run with: streamlit run app.py
"""

import os
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

import db
import ai_helpers

load_dotenv()

st.set_page_config(
    page_title="AI Business Insights Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------
# Data loading (cached so we don't hit SQLite on every interaction)
# ---------------------------------------------------------------------

@st.cache_data
def load_kpis():
    return db.total_kpis().iloc[0]


@st.cache_data
def load_monthly():
    return db.revenue_by_month()


@st.cache_data
def load_by_product():
    return db.revenue_by_product()


@st.cache_data
def load_by_region():
    return db.revenue_by_region()


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

st.sidebar.title("📊 AI Business Insights")
st.sidebar.markdown("Ask plain-English questions about your sales data.")

def _has_gemini_key() -> bool:
    if os.environ.get("GEMINI_API_KEY"):
        return True
    try:
        return bool(st.secrets.get("GEMINI_API_KEY"))
    except Exception:
        return False


if not _has_gemini_key():
    st.sidebar.warning(
        "No GEMINI_API_KEY found. AI features (summary, Q&A, "
        "recommendations) will not work until you set one in your .env file "
        "(locally) or app Secrets (on Streamlit Cloud)."
    )

page = st.sidebar.radio(
    "Navigate",
    ["KPI Dashboard", "Ask a Question", "AI Summary & Recommendations"],
)

# ---------------------------------------------------------------------
# Page: KPI Dashboard
# ---------------------------------------------------------------------

if page == "KPI Dashboard":
    st.title("KPI Dashboard")

    kpis = load_kpis()
    monthly = load_monthly()
    by_product = load_by_product()
    by_region = load_by_region()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", f"${kpis['total_revenue']:,.0f}")
    c2.metric("Total Profit", f"${kpis['total_profit']:,.0f}")
    c3.metric("Total Orders", f"{int(kpis['total_orders']):,}")
    c4.metric("Avg Order Value", f"${kpis['avg_order_value']:,.0f}")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Revenue & Profit by Month")
        fig = px.line(
            monthly, x="year_month", y=["revenue", "profit"],
            markers=True, labels={"value": "USD", "year_month": "Month"},
        )
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.subheader("Revenue by Region")
        fig2 = px.pie(by_region, names="region", values="revenue", hole=0.4)
        st.plotly_chart(fig2, width='stretch')

    st.subheader("Revenue by Product")
    fig3 = px.bar(
        by_product.sort_values("revenue", ascending=True),
        x="revenue", y="product", orientation="h", color="category",
    )
    st.plotly_chart(fig3, width='stretch')

    with st.expander("View raw product table"):
        st.dataframe(by_product, width='stretch')

# ---------------------------------------------------------------------
# Page: Ask a Question (Natural Language Q&A)
# ---------------------------------------------------------------------

elif page == "Ask a Question":
    st.title("Ask a Question About Your Business")
    st.caption(
        "Examples: \"Why did sales drop last month?\" · "
        "\"Which products are losing revenue?\" · "
        "\"What should we do next quarter?\""
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("Ask a question about your sales data...")

    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing your data..."):
                try:
                    answer = ai_helpers.answer_question(
                        question, history=st.session_state.chat_history[:-1]
                    )
                except Exception as e:
                    answer = f"Error calling AI: {e}"
                st.markdown(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

# ---------------------------------------------------------------------
# Page: AI Summary & Recommendations
# ---------------------------------------------------------------------

elif page == "AI Summary & Recommendations":
    st.title("AI Executive Summary & Recommendations")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Executive Summary")
        if st.button("Generate Summary"):
            with st.spinner("Generating executive summary..."):
                try:
                    summary = ai_helpers.generate_executive_summary()
                    st.session_state["summary"] = summary
                except Exception as e:
                    st.error(f"Error: {e}")
        if "summary" in st.session_state:
            st.info(st.session_state["summary"])

    with col2:
        st.subheader("Recommendations")
        if st.button("Generate Recommendations"):
            with st.spinner("Generating recommendations..."):
                try:
                    recs = ai_helpers.generate_recommendations()
                    st.session_state["recs"] = recs
                except Exception as e:
                    st.error(f"Error: {e}")
        if "recs" in st.session_state:
            st.success(st.session_state["recs"])
