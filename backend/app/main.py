import os
import logging
import time
import secrets
from dotenv import find_dotenv, load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for env_file in [
    os.path.join(BACKEND_DIR, ".env"),
    os.path.join(os.path.dirname(BACKEND_DIR), ".env"),
    find_dotenv(),
]:
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file, override=False)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.db import get_database_status

from app.api.requirement_routes import router as requirement_router
from app.api.custom_box_routes import router as custom_box_router
from app.api.packing_routes import router as packing_router
from app.api.product_routes import router as product_router
from app.api.package_routes import router as package_router
from app.api.cart_routes import router as cart_router

if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("app").setLevel(logging.INFO)
logger = logging.getLogger(__name__)
API_KEY = os.getenv("API_KEY", "").strip()
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="3D Packing Optimizer API",
    description="Agentic 3D Packing Optimizer: Part requirement parsing, custom box sizing, padding calculation, and 3D spatial packing optimization.",
    version="1.0.0",
)


@app.middleware("http")
async def log_request_duration(request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("http.request.failed method=%s path=%s duration_ms=%.2f", request.method, request.url.path, (time.perf_counter() - started) * 1000)
        raise
    logger.info("http.request.completed method=%s path=%s status=%s duration_ms=%.2f", request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000)
    return response


@app.middleware("http")
async def require_api_key_when_configured(request: Request, call_next):
    """Protect API routes and bind chat sessions to an identity supplied by a trusted auth proxy."""
    if API_KEY and request.url.path.startswith("/api/") and request.method != "OPTIONS":
        supplied_key = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(supplied_key, API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    if request.url.path.startswith("/api/requirements/workflow"):
        user_id = request.headers.get("X-Authenticated-User") if API_KEY else "local"
        if API_KEY and not user_id:
            return JSONResponse(status_code=401, content={"detail": "Authenticated user identity is required"})
        request.state.authenticated_user_id = user_id or "local"
    return await call_next(request)

# Enable CORS for frontend applications (e.g. Vite on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(product_router, prefix="/api")
app.include_router(package_router, prefix="/api")
app.include_router(cart_router, prefix="/api")
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
            "products": "/api/products",
            "packages": "/api/packages",
            "cart": "/api/cart",
            "requirements": "/api/requirements",
            "custom_box": "/api/custom-box",
            "packing": "/api/packing",
            "docs": "/docs",
            "openapi": "/openapi.json",
        },
    }


@app.get("/health", summary="Health check endpoint")
def health_check():
    database = get_database_status()
    return {"status": "healthy" if database.get("healthy") else "degraded", "database": database}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
