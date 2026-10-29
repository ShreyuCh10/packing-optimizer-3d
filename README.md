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
- **Benchmark Dataset**: Includes 50 realistic industrial parts in `products_dataset.csv` with size and weight variety.
