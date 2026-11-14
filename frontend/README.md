# BHIMA — Earth System Intelligence (Frontend)

Production-quality React 18 / TypeScript 5 / Vite 5 application for NASA Space Apps Challenge 2024.

## Design Philosophy

- **Tone**: Professional, minimal, calm, trustworthy scientific software.
- **Palette**:
  - Background: `#F7F8F6`
  - Primary Surface: `#FFFFFF`
  - Primary Text: `#202824`
  - Secondary Text: `#69736D`
  - Primary Accent: `#31594B`
  - Secondary Accent: `#84978B`
  - Borders: `#E4E8E4`
  - Subtle Surface: `#EEF1ED`
- **Typography**: Inter (Google Fonts)
- **Icons**: Lucide React
- **Guarantees**: No synthetic metrics, no fabricated testimonials, no neon/particles, strict scientific and statistical integrity.

## Technology Stack

- **Framework**: React 18 + Vite 5 + TypeScript 5
- **Styling**: Tailwind CSS 3
- **State Management**: Zustand v4 + TanStack Query v5
- **Mapping**: MapLibre GL JS with OpenStreetMap raster basemap (no proprietary API keys required)
- **Visualization**: Plotly.js (`plotly.js-basic-dist-min` + `react-plotly.js`)
- **Routing**: React Router DOM v6

## Directory Layout

```
frontend/
  src/
    main.tsx                  # Application entry point
    App.tsx                   # React Router & QueryClient setup
    index.css                 # Base theme and MapLibre imports
    types/
      index.ts                # TypeScript contracts matching backend schemas
      plotly-modules.d.ts     # Plotly module typing
    api/
      client.ts               # Native fetch client with error handling
      queries.ts              # TanStack Query hooks (useDatasets, useTimeSeries, etc.)
    store/
      investigationStore.ts   # Zustand state with 8 geographic presets & localStorage cache
    components/
      ui/                     # Button, Card, Badge, Spinner, EmptyState, ErrorState, Tooltip
      layout/                 # Header, Sidebar, AppShell
      map/                    # ExplorerMap (MapLibre), RegionSelector, MapLegend
      charts/                 # PlotWrapper, TimeSeriesChart, TrendChart, ComparisonChart
      analysis/               # AnalysisPanel, TrendCard, StatisticsCard, SourceInfo
    pages/
      LandingPage.tsx         # Minimal public landing page
      OverviewPage.tsx        # System dashboard & recent investigations
      ExplorerPage.tsx        # Interactive map + investigation execution
      InvestigationPage.tsx   # Detailed trend, statistics, and CSV export
      ComparePage.tsx         # Dual-region comparison workflow
      AgentPage.tsx           # Full-height tool-calling Ask BHIMA chat interface
      DataSourcesPage.tsx     # NASA GPM IMERG and MODIS LST metadata documentation
      MethodologyPage.tsx     # Mann-Kendall and Sen's slope mathematical documentation
```

## Running the Application

```bash
# 1. Install dependencies
npm install

# 2. Start development server
npm run dev

# 3. Build for production
npm run build
```

Backend service is configured to connect to `http://localhost:8000` via `VITE_API_URL`.
