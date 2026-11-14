# BHIMA — Google Cloud Platform (GCP) Production Deployment Guide

This guide describes the complete, production-ready deployment architecture for **BHIMA — Earth System Intelligence** on Google Cloud Platform (GCP).

---

## 1. Architecture Overview

BHIMA's cloud architecture is designed for **extreme performance (<10ms queries)**, **zero runtime remote bottlenecks**, and **strict scientific data provenance**:

```
                              [ User Web Browser ]
                                       │
                         HTTPS (Port 443 / Cloud Run)
                                       ▼
                     ┌───────────────────────────────────┐
                     │     Frontend Container (Nginx)    │
                     │  - React 18 + Vite SPA Build      │
                     │  - Static Asset Caching & Gzip    │
                     │  - Security Headers & Healthcheck │
                     └─────────────────┬─────────────────┘
                                       │ /api/ (or CORS)
                                       ▼
                     ┌───────────────────────────────────┐
                     │      Backend Container (Cloud Run)│
                     │  - FastAPI / Python 3.12-slim     │
                     │  - Multi-worker Uvicorn           │
                     │  - Port 8080 ($PORT dynamic)      │
                     │  - Preloaded SQLite Observations  │
                     └─────────┬──────────────────┬──────┘
                               │                  │
                Application Default Credentials   │ Secret Manager
                               │                  │ ($GEMINI_API_KEY)
                               ▼                  ▼
                     ┌──────────────────┐  ┌──────────────────┐
                     │ Google Cloud     │  │ GCP Secret       │
                     │ Storage (GCS)    │  │ Manager          │
                     │ - Bucket:        │  └──────────────────┘
                     │   gs://<bucket>  │
                     │ - SQLite sync    │
                     │ - Parquet chunks │
                     └─────────▲────────┘
                               │
                Cloud Run Job (Batch Preprocessor)
                     ┌───────────────────────────────────┐
                     │  Offline Preprocessor / Ingestion │
                     │  - preprocess_and_upload.py       │
                     │  - Extract from MPC STAC / Zarr   │
                     │  - Uploads verified DB to GCS     │
                     └───────────────────────────────────┘
```

### Key Architectural Principles
1. **Zero Remote Zarr During User Requests**: User requests hit preprocessed, validated persistent SQLite records in `<10ms`.
2. **Zero Mock Data**: 100% real NASA GPM IMERG and Microsoft Planetary Computer satellite observations.
3. **Zero Hardcoded Credentials**: Uses Google Application Default Credentials (ADC) and GCP Secret Manager.
4. **Zero-Credential Local Development**: Automatically falls back to `LocalStorageService` locally without needing GCP access.

---

## 2. Prerequisites & Tools

- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated.
- Docker 24+ installed locally (for local builds) or Cloud Build.
- A GCP project with Billing enabled.

Set your shell environment variables:
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export GCS_BUCKET="bhima-observations-${PROJECT_ID}"
export BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/bhima-repo/backend:latest"
export FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/bhima-repo/frontend:latest"

gcloud config set project $PROJECT_ID
```

---

## 3. Enable Required Google Cloud APIs

Enable the core APIs required for Serverless Containers, Storage, and Secrets:

```bash
gcloud services enable \
    run.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com
```

---

## 4. Persistent Storage Setup (Google Cloud Storage)

Create a regional GCS bucket to store preprocessed satellite databases and compressed Parquet files:

```bash
# Create standard regional bucket
gcloud storage buckets create gs://${GCS_BUCKET} \
    --location=${REGION} \
    --uniform-bucket-level-access

# Configure CORS on the bucket (optional if proxying through backend)
cat <<EOF > /tmp/gcs-cors.json
[
  {
    "origin": ["*"],
    "responseHeader": ["Content-Type", "ETag"],
    "method": ["GET", "HEAD"],
    "maxAgeSeconds": 3600
  }
]
EOF
gcloud storage buckets update gs://${GCS_BUCKET} --cors-file=/tmp/gcs-cors.json
rm /tmp/gcs-cors.json
```

---

## 5. Least-Privilege IAM & Service Account

Create a dedicated runtime service account for BHIMA:

```bash
# Create Service Account
gcloud iam service-accounts create bhima-app-sa \
    --display-name="BHIMA Cloud Run Runtime Service Account"

export SA_EMAIL="bhima-app-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant read/write access only to the BHIMA GCS bucket
gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

# Grant Secret Manager Accessor role for AI keys
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"
```

---

## 6. Secret Manager Setup (Gemini AI Key)

Store your Gemini AI API key securely:

```bash
# Create the secret
echo -n "YOUR_GEMINI_API_KEY_HERE" | gcloud secrets create GEMINI_API_KEY \
    --data-file=- \
    --replication-policy="automatic"
```

---

## 7. Artifact Registry Setup

Create a Docker repository in Artifact Registry:

```bash
gcloud artifacts repositories create bhima-repo \
    --repository-format=docker \
    --location=${REGION} \
    --description="BHIMA Docker Repository"

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 8. Build & Push Docker Images

### Option A: Using Google Cloud Build (Recommended — No local Docker required)

```bash
# Build and push Backend image
gcloud builds submit backend \
    --tag ${BACKEND_IMAGE}

# Build and push Frontend image
gcloud builds submit frontend \
    --tag ${FRONTEND_IMAGE}
```

### Option B: Local Docker Build

```bash
# Backend build
docker build -t ${BACKEND_IMAGE} backend/
docker push ${BACKEND_IMAGE}

# Frontend build (injecting production API base URL)
docker build -t ${FRONTEND_IMAGE} frontend/
docker push ${FRONTEND_IMAGE}
```

---

## 9. Deploy Backend to Cloud Run

Deploy the backend with automatic scaling, health probes, and persistent GCS integration:

```bash
gcloud run deploy bhima-backend \
    --image=${BACKEND_IMAGE} \
    --region=${REGION} \
    --platform=managed \
    --service-account=${SA_EMAIL} \
    --allow-unauthenticated \
    --port=8080 \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --set-env-vars="STORAGE_BACKEND=gcs,BHIMA_GCS_BUCKET=${GCS_BUCKET},ENVIRONMENT=production,CORS_ORIGINS=*" \
    --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest"
```

Retrieve the backend URL:
```bash
export BACKEND_URL=$(gcloud run services describe bhima-backend --region=${REGION} --format='value(status.url)')
echo "Backend URL: ${BACKEND_URL}"
```

---

## 10. Deploy Frontend to Cloud Run

Deploy the frontend container, pointing to the newly deployed backend:

```bash
gcloud run deploy bhima-frontend \
    --image=${FRONTEND_IMAGE} \
    --region=${REGION} \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=5 \
    --set-env-vars="VITE_API_BASE_URL=${BACKEND_URL}"
```

Retrieve the frontend URL:
```bash
export FRONTEND_URL=$(gcloud run services describe bhima-frontend --region=${REGION} --format='value(status.url)')
echo "BHIMA Application URL: ${FRONTEND_URL}"
```

---

## 11. Run Offline Preprocessor (Cloud Run Job)

To update the persistent observations database without impacting the live web application:

```bash
# Create the Cloud Run Job
gcloud run jobs create bhima-ingest-worker \
    --image=${BACKEND_IMAGE} \
    --region=${REGION} \
    --service-account=${SA_EMAIL} \
    --tasks=1 \
    --memory=4Gi \
    --cpu=2 \
    --task-timeout=3600s \
    --command="python" \
    --args="scripts/preprocess_and_upload.py,--upload-only" \
    --set-env-vars="STORAGE_BACKEND=gcs,BHIMA_GCS_BUCKET=${GCS_BUCKET}"

# Execute the ingestion job on-demand
gcloud run jobs execute bhima-ingest-worker --region=${REGION}
```

---

## 12. Verification & Health Probes

Run these commands to verify the live production deployment:

### Backend Liveness Probe
```bash
curl -f "${BACKEND_URL}/healthz"
# Expected response:
# {"status":"ok","timestamp":"...","service":"BHIMA Earth System Intelligence API","version":"1.2.0","environment":"production"}
```

### Backend Readiness Probe
```bash
curl -f "${BACKEND_URL}/readiness"
# Expected response:
# {"status":"ready","persistent_store_ready":true,"timestamp":"..."}
```

### Preprocessed Observation Latency Test (<10ms)
```bash
curl -X POST "${BACKEND_URL}/analysis/timeseries" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "GPM_3IMERGM_07",
    "region": {
      "name": "Gujarat, India",
      "min_lon": 73.10, "max_lon": 73.30,
      "min_lat": 22.10, "max_lat": 22.50
    },
    "start_date": "2015-01",
    "end_date": "2020-12"
  }'
# Expected: Returns 72 months of real satellite data with data_provenance: "REAL_NASA_DATA" in <10ms.
```

---

## 13. Local Development (Zero GCP Credentials)

To run the application locally without any Google Cloud account or credentials:

```bash
# 1. Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Frontend
cd frontend
npm install
npm run dev
```

The system automatically detects the absence of GCS configuration and uses `LocalStorageService` with the embedded `backend/data/bhima_observations.db` database. All 9 regions and 72 months of NASA observations are available immediately with zero latency and zero cloud costs.
