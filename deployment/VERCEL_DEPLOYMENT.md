# BHIMA — Vercel Production Deployment Guide

This guide describes how to deploy **BHIMA — Earth System Intelligence** on **Vercel**, including the React 18/Vite frontend and FastAPI Python serverless backend, preserving all real NASA and Microsoft Planetary Computer data pipelines.

---

## 1. Architectural Strategy: Two-Project Monorepo (Recommended)

To achieve maximum performance and stability on Vercel without Serverless Function size limit issues:

```
                               [ Web Client / Browser ]
                                          │
                 ┌────────────────────────┴────────────────────────┐
                 │                                                 │
          HTTPS (Port 443)                                  HTTPS (Port 443)
                 │                                                 │
                 ▼                                                 ▼
      ┌─────────────────────┐                          ┌────────────────────────┐
      │  bhima-frontend     │                          │  bhima-api             │
      │  (Vercel Project 1) │                          │  (Vercel Project 2)    │
      │  - Root: frontend/  │                          │  - Root: backend/      │
      │  - Framework: Vite  │                          │  - Framework: Other    │
      │  - Global Edge CDN  │                          │  - Python 3.12 Runtime │
      │  - SPA Rewrites     │                          │  - Entry: api/index.py │
      └──────────┬──────────┘                          └───────────┬────────────┘
                 │                                                 │
                 │ VITE_API_BASE_URL                               │ Reads <10ms
                 └─────────────────────────────────────────────────┼────────────┐
                                                                   ▼            ▼
                                                         ┌──────────────────┐ ┌──────────────────┐
                                                         │ Seed SQLite DB   │ │ Vercel Blob /    │
                                                         │ in /tmp (572 KB) │ │ S3 Object Storage│
                                                         │ (1,088 real obs) │ │ (Persistent sync)│
                                                         └──────────────────┘ └──────────────────┘
```

### Why Option A (Two Vercel Projects) is Recommended
1. **Frontend**: Built instantly on Vercel's global CDN with zero serverless cold starts.
2. **Backend**: Clean Python 3.12 Serverless Function in `backend/` using `backend/api/index.py`.
3. **Bundle Size**: Prunes heavy build tools (`dask`, `netCDF4`, `google-cloud-*`) to stay safely under Vercel's **250 MB** uncompressed limit (~180 MB actual).
4. **Resilience**: The frontend continues serving even during backend function cold starts.

*(Note: A single unified project option is also supported via the root `vercel.json`).*

---

## 2. Prerequisites

1. A [Vercel account](https://vercel.com/signup).
2. [Vercel CLI](https://vercel.com/docs/cli) installed:
   ```bash
   npm install -g vercel
   ```
3. Authenticate with Vercel:
   ```bash
   vercel login
   ```
4. Push your repository to GitHub / GitLab / Bitbucket.

---

## 3. Step-by-Step Deployment (Option A: Two Vercel Projects)

### Project 1: Backend API (`bhima-api`)

1. Open the [Vercel Dashboard](https://vercel.com/new).
2. Import your Git repository.
3. In **Project Configuration**:
   - **Project Name**: `bhima-api`
   - **Framework Preset**: `Other`
   - **Root Directory**: Click *Edit* and select **`backend`**
   - **Build Command**: Leave empty (handled automatically by `@vercel/python`)
   - **Output Directory**: Leave empty
4. In **Environment Variables**, add:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables production mode |
   | `STORAGE_BACKEND` | `local` (or `vercel_blob`) | Storage driver |
   | `CORS_ORIGINS` | `https://*.vercel.app,*` | Allows frontend requests |
   | `GEMINI_API_KEY` | `your_gemini_key` *(Optional)* | For Ask BHIMA assistant |
   | `NASA_EARTHDATA_USERNAME` | *(Optional)* | Direct GES DISC credentials |
   | `NASA_EARTHDATA_PASSWORD` | *(Optional)* | Direct GES DISC credentials |
5. Click **Deploy**.
6. Once deployed, copy your backend URL (e.g., `https://bhima-api.vercel.app`).

#### Optional: Enable Persistent Managed Cloud Database (Vercel Postgres / Neon / Supabase)
BHIMA features a dual-engine database layer (`backend/app/core/db_engine.py`).
- **Default (Zero Credentials)**: Uses bundled SQLite (`bhima_observations.db`) seeded into `/tmp`. This provides instant sub-10ms reads for all 1,088 pre-cached NASA observations across the 9 canonical regions.
- **Persistent Cloud Writes (Recommended for Production)**: When users investigate custom bounding boxes or date ranges at runtime, the application caches newly retrieved observations. Because serverless containers have ephemeral filesystems, runtime SQLite writes to `/tmp` are wiped when the container recycles. To ensure persistent writes across invocations, attach a managed PostgreSQL instance:

1. In your `bhima-api` project in the [Vercel Dashboard](https://vercel.com/dashboard), navigate to the **Storage** tab.
2. Click **Create Database** -> select **Postgres** (powered by Neon).
3. Choose your region (e.g. `Washington, D.C. (iad1)` or matching your function region) and click **Create**.
4. Vercel automatically injects `POSTGRES_URL`, `DATABASE_URL`, `POSTGRES_PRISMA_URL`, etc., into your project's Environment Variables.
5. **Migrate existing observations**: Run the included migration script from your machine:
   ```bash
   cd backend
   POSTGRES_URL="your_vercel_postgres_connection_string" python scripts/migrate_sqlite_to_postgres.py
   ```
   This reads all 1,088 records from `backend/data/bhima_observations.db`, creates the necessary relational tables and indices in PostgreSQL, and verifies 100% record parity with zero data loss.
6. The FastAPI backend automatically detects `POSTGRES_URL` and routes all cache lookups and runtime inserts to PostgreSQL via atomic upserts (`INSERT ... ON CONFLICT (...) DO UPDATE`).

#### Optional: Enable Vercel Blob Storage (for Parquet & Database Backups)
1. In the `bhima-api` Vercel dashboard, go to the **Storage** tab.
2. Click **Create Database** -> select **Blob**.
3. Name it `bhima-blob` and click **Create**.
4. Vercel automatically injects `BLOB_READ_WRITE_TOKEN` into your project environment variables.
5. In project settings, set `STORAGE_BACKEND=vercel_blob`.

---

### Project 2: Frontend (`bhima-frontend`)

1. Go back to [Vercel Dashboard](https://vercel.com/new).
2. Import the **same repository** a second time.
3. In **Project Configuration**:
   - **Project Name**: `bhima-frontend`
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click *Edit* and select **`frontend`**
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://bhima-api.vercel.app` | URL from Project 1 |
5. Click **Deploy**.
6. Once deployed, open your live application (e.g., `https://bhima-frontend.vercel.app`).

---

## 4. Alternative: Deploying via Vercel CLI

You can also deploy directly from the command line:

### Deploy Backend:
```bash
cd backend
vercel --prod
# Follow the interactive prompts:
# - Link to existing project? No
# - Project name: bhima-api
# - In which directory is your code located? ./
```

### Deploy Frontend:
```bash
cd frontend
vercel --prod --build-env VITE_API_BASE_URL=https://bhima-api.vercel.app
```

---

## 5. Serverless Architecture & Execution Constraints

### Request-Driven Serverless Operations (<10ms)
The user-facing Vercel functions execute request-driven analytical queries:
- **FastAPI Core**: Serves `/health`, `/readiness`, `/datasets/`, `/analysis/*`, `/agent/chat`.
- **High-Performance Storage**: Reads preprocessed observations directly from SQLite (`bhima_observations.db`) or Vercel Blob in `<10ms`.
- **Scientific Computations**: Bounded Mann-Kendall trend tests, Sen's slopes, descriptive statistics (`scipy`, `pandas`, `numpy`, `pymannkendall`).
- **Read-Only Filesystem Resolution**: On Vercel, the function container filesystem is read-only. BHIMA automatically seeds the bundled database into `/tmp/bhima_observations.db` on cold start (~2ms), enabling SQLite locks and queries without error.

### Heavy Background Operations (Isolate to Batch Workers)
The following operations **must not** be executed inside short-lived Vercel serverless HTTP requests:
- Downloading multi-gigabyte NASA GPM IMERG HDF5 or Microsoft Planetary Computer Zarr chunks.
- Running unconstrained Dask distributed arrays over global grids.
- Preprocessing 72 months for new global regions from scratch.

These operations are isolated in `backend/scripts/preprocess_and_upload.py` and run on demand or as a scheduled workflow.

---

## 6. Offline Data Preprocessing Workflow

To ingest new regions or refresh the 72-month archive:

1. Run the preprocessor locally or in GitHub Actions with full worker dependencies:
   ```bash
   cd backend
   pip install -r requirements-worker.txt
   python scripts/preprocess_and_upload.py --workers 8
   ```
2. The script:
   - Connects to Microsoft Planetary Computer STAC & Zarr archives.
   - Extracts real satellite observations.
   - Computes monthly spatial integrals.
   - Verifies statistical coverage.
   - Saves to `backend/data/bhima_observations.db`.
   - Uploads the updated database to Vercel Blob (`databases/bhima_observations.db`).
3. The deployed Vercel functions automatically sync the updated database on their next cold start.

---

## 7. Verification & Health Probes

Verify the deployed Vercel backend using curl or your browser:

### 1. Health Probe
```bash
curl -f "https://bhima-api.vercel.app/health"
# Response:
# {"status":"ok","service":"BHIMA Earth System Intelligence API","version":"1.0.0","environment":"production"}
```

### 2. Readiness Probe
```bash
curl -f "https://bhima-api.vercel.app/readiness"
# Response:
# {"status":"ready","persistent_store_ready":true,"timestamp":"..."}
```

### 3. Preprocessed Gujarat Investigation (<10ms)
```bash
curl -X POST "https://bhima-api.vercel.app/analysis/timeseries" \
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
# Response:
# Returns 72 months of real NASA GPM observations, Mann-Kendall Sen slope, and provenance REAL_NASA_DATA.
```

---

## 8. Troubleshooting Vercel Deployments

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **`Function bundle exceeds 250 MB`** | Virtual environment or GCP SDKs included in bundle | Ensure `.vercelignore` excludes `venv/`, and use serverless `requirements.txt`. |
| **`sqlite3.OperationalError: attempt to write a readonly database`** | SQLite creating journal in read-only container | Automatic `/tmp` seeding in `persistent_cache.py` resolves this. |
| **`404 Not Found on page refresh`** | React Router SPA routing not rewritten | `frontend/vercel.json` rewrites `/(.*)` to `/index.html`. |
| **`CORS Error in Browser`** | `CORS_ORIGINS` missing frontend domain | Set `CORS_ORIGINS=https://*.vercel.app,*` in backend project settings. |
| **`VITE_API_BASE_URL undefined`** | Environment variable missing in frontend project | Set `VITE_API_BASE_URL` in Project Settings -> Environment Variables and redeploy. |
| **`No data for custom region`** | Region not in the 9 preprocessed canonical regions | Run `scripts/preprocess_and_upload.py` to ingest the new bounding box. |
