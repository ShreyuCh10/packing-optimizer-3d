from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.requirement_routes import router as requirement_router
from app.api.custom_box_routes import router as custom_box_router
from app.api.packing_routes import router as packing_router

app = FastAPI(
    title="3D Packing Optimizer API",
    description="Agentic 3D Packing Optimizer: Part requirement parsing, custom box sizing, padding calculation, and 3D spatial packing optimization.",
    version="1.0.0",
)

# Enable CORS for frontend applications (e.g. Vite on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(requirement_router, prefix="/api")
app.include_router(custom_box_router, prefix="/api")
app.include_router(packing_router, prefix="/api")


@app.get("/", summary="Root health & status")
def root():
    return {
        "status": "online",
        "service": "3D Packing Optimizer API",
        "version": "1.0.0",
        "endpoints": {
            "requirements": "/api/requirements",
            "custom_box": "/api/custom-box",
            "packing": "/api/packing",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
    }


@app.get("/health", summary="Health check endpoint")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
