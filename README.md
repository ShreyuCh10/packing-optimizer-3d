# 3D Packing Optimizer

An intelligent 3D packaging and spatial packing optimization platform powered by LangGraph, FastAPI, Three.js, and combinatorial geometry algorithms.

For the complete technical documentation and architecture history, see **[PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md)**.

## Quick Start

### 1. Backend Setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API Documentation & Interactive Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

To enable GPT-5.1 package recommendations, copy `backend/.env.example` to `backend/.env` and set
`AZURE_FOUNDRY_OPENAI_BASE_URL`, `AZURE_FOUNDRY_OPENAI_API_KEY`, and
`AZURE_FOUNDRY_OPENAI_MODEL` to your Azure AI Foundry OpenAI-compatible v1 endpoint details.
Without those values, the workflow still chooses among packages that pass deterministic 3D fit
and weight checks, using a visible deterministic fallback recommendation.

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

## Core Features
- **AI Requirement Agent**: Extracts structured part requirements from natural language using LangGraph and LayaRouter.
- **Custom Box Sizing**: Calculates multi-unit layouts, padding clearance, container dimensions, weights, and carrier limits.
- **3D Spatial Packing**: Fits parts into standard or custom containers with 6-degree orthogonal rotations and Three.js visualization output.
- **Package Recommendation Agent**: Ranks only packages confirmed to fit, explains its selection, and displays the selected package and packed product in 3D (CAD model when available; dimension-accurate boxes otherwise).
- **Benchmark Dataset**: Includes 50 realistic industrial parts in `products_dataset.csv` with size and weight variety.

Package candidates use their actual names and dimensions from `backend/data/packages.csv`, including
when the SQLite package table has not been migrated. Item-volume utilization is the product volume
divided by container volume; the padded-bounding-box estimate is shown separately. The source data
does not specify carton construction, protection ratings, or stock counts. Heavy-duty pallet and
stillage records also lack payload ratings, so they are not recommended for weighted shipments until
verified ratings are added.
