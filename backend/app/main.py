"""FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import dns as _models  # noqa: F401  (register tables)
from app.routers import auth, hosted_zones, records, stats
from app.services.seed import seed_if_empty

Base.metadata.create_all(bind=engine)
try:
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
except Exception:
    # Never crash startup because of seeding; tables are already created.
    pass

app = FastAPI(title="Route53 Clone API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(hosted_zones.router, prefix="/api/hosted-zones", tags=["hosted-zones"])
app.include_router(records.router, prefix="/api/hosted-zones/{zone_id}/records", tags=["records"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.get("/api/health", tags=["health"])
def health():
    return {"ok": True, "service": "route53-clone"}


@app.get("/", include_in_schema=False)
def root():
    return {"service": "route53-clone", "docs": "/api/docs", "health": "/api/health"}
