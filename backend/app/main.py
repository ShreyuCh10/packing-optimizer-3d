
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.custom_box_routes import router as custom_box_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory containing converted product GLB models.
MODELS_DIR = Path(__file__).resolve().parents[1] / "data" / "models"

app.mount(
    "/models",
    StaticFiles(directory=str(MODELS_DIR)),
    name="models",
)

app.include_router(custom_box_router)
