"""
main.py — FastAPI application entry point.

Run:
    uvicorn backend.main:app --reload --port 8000

Swagger UI:  http://localhost:8000/docs
ReDoc:       http://localhost:8000/redoc
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import analytics, ports, trade

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Port-Wise Trade Analytics API",
    description=(
        "REST API powering the Port-Wise Trade Analytics platform. "
        "Provides endpoints for ports, trade trends, commodities, "
        "trading partners, and high-level analytics for 10 major Indian ports "
        "spanning 2019–2024."
    ),
    version="1.0.0",
    contact={"name": "Port-Wise Trade Analytics"},
    license_info={"name": "MIT"},
)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(ports.router,     prefix="/api/ports",     tags=["Ports"])
app.include_router(trade.router,     prefix="/api/trade",     tags=["Trade"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
def health_check():
    """Liveness probe — returns API version and status."""
    return {"status": "healthy", "version": "1.0.0", "service": "Port-Wise Trade Analytics API"}


@app.get("/", tags=["System"])
def root():
    return {"message": "Welcome to Port-Wise Trade Analytics API. Visit /docs for Swagger UI."}
