from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.custom_box_routes import router as custom_box_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(custom_box_router)


