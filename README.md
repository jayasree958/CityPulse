# CityPulse — Community Decision Intelligence Assistant

Gen AI Academy APAC Edition · **AI for Better Living and Smarter Communities**

Helps city stakeholders see which service-request categories and districts
are most backlogged, and lets them ask plain-English questions to get an
instant, data-grounded recommendation from Gemini.

## Stack
- Google BigQuery — data layer (`bigquery-public-data.austin_311`, no data upload needed)
- Gemini API — conversational analytics / decision-intelligence layer
- Streamlit + Plotly — dashboard
- Google Cloud Run — deployment

## 1. Get a free Gemini API key (2 min)
Go to https://aistudio.google.com/apikey → Create API key → copy it.

## 2. Deploy to Cloud Run (copy-paste, in order)

```bash
# One-time setup
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com bigquery.googleapis.com cloudbuild.googleapis.com

# Deploy straight from source, passing your Gemini key as an env var
gcloud run deploy citypulse \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars GEMINI_API_KEY=YOUR_GEMINI_KEY

# Grant the Cloud Run service account permission to run BigQuery jobs
gcloud iam service-accounts list   # find the service account email

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/bigquery.jobUser"
```

`gcloud run deploy --source .` builds the Dockerfile and deploys in one
step, printing a public `*.run.app` URL — that's your submission link.

## Local test (optional)
```bash
pip install -r requirements.txt
gcloud auth application-default login
export GEMINI_API_KEY=your_key
streamlit run app.py
```

## Troubleshooting
- If the BigQuery query errors on a column name, run
  `bq show bigquery-public-data:austin_311.311_service_requests` to confirm
  the schema and adjust `app.py`'s query if needed.
- If Gemini answers are blank, double check `GEMINI_API_KEY` is set on the
  Cloud Run service (Cloud Run console → service → Edit & Deploy New
  Revision → Variables).
