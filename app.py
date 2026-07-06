"""
CityPulse — Community Decision Intelligence Assistant
Gen AI Academy APAC Edition — "AI for Better Living and Smarter Communities"
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="CityPulse", page_icon="🏙️", layout="wide")

# Get API Key from Streamlit Secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-flash"

@st.cache_data(ttl=3600)
def load_311_data(days_back: int = 365):
    # Dummy data to ensure the app loads without BigQuery errors
    data = {
        "complaint_type": ["Pothole", "Graffiti", "Noise Complaint", "Trash Pickup", "Street Light Out"],
        "council_district_code": ["1", "2", "1", "3", "4"],
        "status": ["Open", "Closed", "Open", "Open", "Closed"],
        "resolution_hours": [24.5, 2.0, 48.0, 12.5, 5.0]
    }
    return pd.DataFrame(data)

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    # Aggregation logic
    g = df.groupby("complaint_type").agg(
        total_requests=("complaint_type", "count"),
        open_requests=("status", lambda s: (s == "Open").sum()),
        avg_resolution_hours=("resolution_hours", "mean"),
    ).reset_index()
    g["avg_resolution_hours"] = g["avg_resolution_hours"].round(1)
    g["backlog_score"] = (g["open_requests"] * 0.6 + g["avg_resolution_hours"] * 0.4).round(1)
    return g.sort_values("backlog_score", ascending=False)

def build_district_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("council_district_code").agg(
        total_requests=("council_district_code", "count"),
        open_requests=("status", lambda s: (s == "Open").sum()),
    ).reset_index()
    return g.sort_values("open_requests", ascending=False)

def ask_gemini(question: str, context_summary: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ Please set GEMINI_API_KEY in Streamlit Secrets."
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"Context: {context_summary}\n\nQuestion: {question}\n\nAnswer concisely:"
    response = model.generate_content(prompt)
    return response.text

# ---------------- UI ----------------
st.title("🏙️ CityPulse — Community Decision Intelligence Assistant")

with st.sidebar:
    st.header("Controls")
    days_back = st.slider("Look-back window (days)", 30, 730, 365)

raw = load_311_data(days_back)
summary = build_summary(raw)
district = build_district_summary(raw)

col1, col2, col3 = st.columns(3)
col1.metric("Requests analyzed", f"{len(raw):,}")
col2.metric("Complaint categories", len(summary))
col3.metric("Currently open", int((raw["status"] == "Open").sum()))

st.subheader("🚨 Top backlogged complaint categories")
fig = px.bar(summary, x="backlog_score", y="complaint_type", orientation="h")
st.plotly_chart(fig, use_container_width=True)

st.subheader("📍 Open requests by council district")
fig2 = px.bar(district, x="council_district_code", y="open_requests")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("💬 Ask CityPulse")
question = st.text_input("Ask a question about this data")
if st.button("Get recommendation") and question:
    context = summary.to_string()
    with st.spinner("Asking Gemini..."):
        st.info(ask_gemini(question, context))
