"""
CityPulse — Community Decision Intelligence Assistant
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

st.set_page_config(page_title="CityPulse", page_icon="🏙️", layout="wide")

# Configuration
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-flash"

@st.cache_data(ttl=3600)
def load_311_data():
    # Static data to ensure the app runs without BigQuery errors
    data = {
        "complaint_type": ["Pothole", "Graffiti", "Noise Complaint", "Trash Pickup", "Street Light Out"],
        "council_district_code": ["1", "2", "1", "3", "4"],
        "status": ["Open", "Closed", "Open", "Open", "Closed"],
        "resolution_hours": [24.5, 2.0, 48.0, 12.5, 5.0]
    }
    return pd.DataFrame(data)

def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("complaint_type").agg(
        total_requests=("complaint_type", "count"),
        open_requests=("status", lambda s: (s == "Open").sum()),
        avg_resolution_hours=("resolution_hours", "mean"),
    ).reset_index()
    g["backlog_score"] = (g["open_requests"] * 0.6 + g["avg_resolution_hours"] * 0.4).round(1)
    return g.sort_values("backlog_score", ascending=False)

def ask_gemini(question: str, context_summary: str) -> str:
    if not GEMINI_API_KEY:
        return "⚠️ API Key not found in Streamlit Secrets."
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = f"Context: {context_summary}\n\nQuestion: {question}\n\nAnswer concisely:"
    response = model.generate_content(prompt)
    return response.text

# UI Layout
st.title("🏙️ CityPulse — Community Decision Intelligence Assistant")

raw = load_311_data()
summary = build_summary(raw)

col1, col2, col3 = st.columns(3)
col1.metric("Requests analyzed", len(raw))
col2.metric("Complaint categories", len(summary))
col3.metric("Currently open", int((raw["status"] == "Open").sum()))

st.subheader("🚨 Top backlogged complaint categories")
fig = px.bar(summary, x="backlog_score", y="complaint_type", orientation="h")
st.plotly_chart(fig, use_container_width=True)

st.subheader("💬 Ask CityPulse")
question = st.text_input("Ask a question about this data")
if st.button("Get recommendation") and question:
    with st.spinner("Asking Gemini..."):
        st.info(ask_gemini(question, summary.to_string()))
