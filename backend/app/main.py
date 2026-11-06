import os
import logging
import time
from dotenv import find_dotenv, load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for env_file in [
    os.path.join(BACKEND_DIR, ".env"),
    os.path.join(os.path.dirname(BACKEND_DIR), ".env"),
    find_dotenv(),
]:
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Enable CORS for frontend applications (e.g. Vite on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
