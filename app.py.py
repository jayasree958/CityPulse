"""
CityPulse — Community Decision Intelligence Assistant
Gen AI Academy APAC Edition — "AI for Better Living and Smarter Communities"

Real user:      City ops / community stakeholders managing 311-style service requests
Problem:        Which issues & districts need attention first, and why?
Data source:    Google BigQuery public dataset `bigquery-public-data.austin_311.311_service_requests`
Pipeline:       BigQuery SQL aggregation -> pandas -> ranked dashboard
GenAI layer:    Gemini API answers natural-language questions using the live aggregated
                stats as grounding context, and generates a stakeholder recommendation —
                this is the "Decision Intelligence" part of the platform.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery

st.set_page_config(page_title="CityPulse", page_icon="🏙️", layout="wide")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


@st.cache_resource
def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=3600)
def load_311_data(days_back: int = 365):
    client = get_bq_client()
    query = f"""
    SELECT
      complaint_type,
      council_district_code,
      status,
      created_date,
      close_date,
      TIMESTAMP_DIFF(close_date, created_date, HOUR) AS resolution_hours
    FROM `bigquery-public-data.austin_311.311_service_requests`
    WHERE created_date >= TIMESTAMP_SUB(
            (SELECT MAX(created_date) FROM `bigquery-public-data.austin_311.311_service_requests`),
            INTERVAL {days_back} DAY)
      AND complaint_type IS NOT NULL
    LIMIT 200000
    """
    return client.query(query).to_dataframe()


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("complaint_type").agg(
        total_requests=("complaint_type", "count"),
        open_requests=("status", lambda s: (s == "Open").sum()),
        avg_resolution_hours=("resolution_hours", "mean"),
    ).reset_index()
    g["avg_resolution_hours"] = g["avg_resolution_hours"].round(1)
    g["backlog_score"] = (
        g["open_requests"] * 0.6
        + g["avg_resolution_hours"].fillna(0) * 0.4
    ).round(1)
    return g.sort_values("backlog_score", ascending=False)


def build_district_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("council_district_code").agg(
        total_requests=("council_district_code", "count"),
        open_requests=("status", lambda s: (s == "Open").sum()),
    ).reset_index()
    return g.sort_values("open_requests", ascending=False)


def ask_gemini(question: str, context_summary: str) -> str:
    if not GEMINI_API_KEY:
        return (
            "⚠️ No GEMINI_API_KEY set on this deployment. Get a free key at "
            "https://aistudio.google.com/apikey and pass it with "
            "`--set-env-vars GEMINI_API_KEY=...` on Cloud Run deploy."
        )
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    prompt = f"""You are a decision-intelligence assistant for city stakeholders reviewing
311 community service request data for Austin.

Here is the current aggregated data (top complaint categories and district stats):
{context_summary}

Stakeholder question: "{question}"

Answer directly and concretely using only the data given above. Then give one
specific, actionable recommendation a city stakeholder could act on this week.
Keep it under 150 words.
"""
    response = model.generate_content(prompt)
    return response.text


# ---------------- UI ----------------

st.title("🏙️ CityPulse — Community Decision Intelligence Assistant")
st.caption(
    "BigQuery (`austin_311` public dataset) + Gemini · "
    "AI for Better Living and Smarter Communities"
)

with st.sidebar:
    st.header("Controls")
    days_back = st.slider("Look-back window (days)", 30, 730, 365)
    st.markdown("---")
    st.markdown(
        "**Why this matters:** city teams get thousands of service requests. "
        "This ranks *which issue types and districts* are most backlogged, "
        "and lets a stakeholder ask questions in plain English to get an "
        "instant, data-grounded recommendation."
    )

with st.spinner("Querying BigQuery..."):
    raw = load_311_data(days_back)

summary = build_summary(raw)
district = build_district_summary(raw)

col1, col2, col3 = st.columns(3)
col1.metric("Requests analyzed", f"{len(raw):,}")
col2.metric("Complaint categories", len(summary))
col3.metric("Currently open", int((raw["status"] == "Open").sum()))

st.subheader("🚨 Top backlogged complaint categories")
top = summary.head(15)
fig = px.bar(
    top.sort_values("backlog_score"),
    x="backlog_score",
    y="complaint_type",
    orientation="h",
    labels={"backlog_score": "Backlog Score", "complaint_type": "Complaint Type"},
    height=550,
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(top, use_container_width=True, hide_index=True)

st.subheader("📍 Open requests by council district")
fig2 = px.bar(
    district.head(15), x="council_district_code", y="open_requests",
    labels={"council_district_code": "District", "open_requests": "Open requests"},
)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("💬 Ask CityPulse (Gemini-powered decision assistant)")
question = st.text_input(
    "Ask a question about this data",
    placeholder="e.g. Which complaint type should we prioritize fixing this month?",
)
if st.button("Get recommendation") and question:
    context = (
        "Top complaint categories (type, total, open, avg resolution hrs, backlog score):\n"
        + top[["complaint_type", "total_requests", "open_requests",
               "avg_resolution_hours", "backlog_score"]].to_string(index=False)
        + "\n\nDistrict open-request counts:\n"
        + district.head(10).to_string(index=False)
    )
    with st.spinner("Asking Gemini..."):
        answer = ask_gemini(question, context)
    st.info(answer)

st.caption("CityPulse · Gen AI Academy APAC Edition · AI for Better Living and Smarter Communities")
