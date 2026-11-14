# BHIMA — Earth System Intelligence

> **NASA Space Apps Challenge** — Earth System Trend Detective  
> Statistically rigorous, AI-augmented environmental time series analysis platform powered by NASA Earth observations.

---

## 🌍 Overview

**BHIMA** (Earth System Intelligence) is an end-to-end analytical platform that bridges NASA satellite remote sensing data with modern statistical climatology and agentic artificial intelligence. Designed for scientists, policy analysts, and citizens, BHIMA automates the retrieval, quality assurance, spatial subsetting, and trend detection of satellite observations.

Key capabilities:
- **Direct NASA Earthdata Access**: Integrated with NASA GES DISC (GPM IMERG) and LP DAAC (MODIS LST) data feeds.
- **Statistically Rigorous Trend Engine**: Hamed-Rao Modified Mann-Kendall test for serial autocorrelation correction, Sen's robust non-parametric slope estimator, and bootstrap confidence intervals.
- **Agentic AI Assistant**: Gemini-powered conversational agent equipped with direct function calling into backend spatial extraction and analysis tools.
- **Reproducible & Transparent**: Open methodology, deterministic pipelines, explicit limitation disclosures, and standard dataset citations.

---

## 🏛️ Architecture Overview

BHIMA is structured into two decoupled tiers:

```
NASA/
├── backend/                  # FastAPI analytical engine
│   ├── app/
│   │   ├── api/routes/       # REST endpoints (health, datasets, analysis, agent)
│   │   ├── core/             # Data access, trend mathematics, Gemini agent
│   │   ├── models/           # Pydantic schemas and validation
│   │   └── utils/            # In-memory TTL caching and logging
│   └── tests/                # Automated pytest suite
└── frontend/                 # Reactive interface (Vite + React / Leaflet)
```

For full architecture diagrams and component interactions, see [ARCHITECTURE.md](file:///C:/Users/Dhriti/Desktop/NASA/ARCHITECTURE.md).

---

## 🚀 Quick Start (Backend)

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Virtual environment support (`venv`)

### 1. Setup Virtual Environment
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` in the `backend/` folder:
```bash
cp .env.example .env
```
Edit `.env` to supply:
- `NASA_EARTHDATA_USERNAME` & `NASA_EARTHDATA_PASSWORD` (register at [NASA Earthdata Login](https://urs.earthdata.nasa.gov/))
- `GEMINI_API_KEY` (get an API key at [Google AI Studio](https://aistudio.google.com/))

*(Note: If credentials are not supplied, BHIMA operates in local synthetic/development fallback mode with explicit UI and data provenance warnings).*

### 4. Run the API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 Testing

Run the automated test suite from the `backend/` directory:
```bash
pytest -v
```
All tests verify descriptive statistics, non-parametric trend computation, boundary validations, synthetic fallbacks, and API route responses.

---

## 🛰️ NASA Data Sources

- **GPM IMERG Monthly (GPM_3IMERGM_07)**: Global Precipitation Measurement Integrated Multi-satellitE Retrievals for GPM. Spatial resolution: 0.1° × 0.1°, monthly from 2000–present.
- **MODIS Terra Land Surface Temperature (MOD11C3_061)**: Monthly 0.05° Land Surface Temperature and Emissivity.

Detailed sensor and product specifications are documented in [DATA_SOURCES.md](file:///C:/Users/Dhriti/Desktop/NASA/DATA_SOURCES.md).

---

## 🔬 Scientific Methodology

BHIMA implements peer-reviewed methodologies for non-parametric environmental trend evaluation:
1. Spatial aggregation across user-defined latitude/longitude bounding boxes.
2. Hamed & Rao (1998) Modified Mann-Kendall test for autocorrelated data.
3. Sen's slope estimator for median rate of change.
4. Percentile bootstrap for 95% confidence intervals.

See [METHODOLOGY.md](file:///C:/Users/Dhriti/Desktop/NASA/METHODOLOGY.md) for mathematical derivations and limitations.
