import logging

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import accounts, analytics, drafts, pipeline, products, web
from app.db.database import get_db

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build the full GTMOS API. Each call returns an independent instance.

    The local/full API (``app`` below) exposes every route. The public demo builds
    its own instance from this factory and wraps it with safeguards
    (see app/api/public.py), so overrides there never leak into this one.
    """
    api = FastAPI(
        title="GTMOS API",
        description="AI GTM Command Center API",
        version="0.1.0",
    )
    for module in (products, accounts, drafts, pipeline, analytics, web):
        api.include_router(module.router)

    @api.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    @api.get("/health")
    def health_check(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            logger.exception("Health check database query failed")
            raise HTTPException(status_code=503, detail="Database unavailable.")
        return {"status": "healthy", "database": "connected"}

    return api


app = create_app()
