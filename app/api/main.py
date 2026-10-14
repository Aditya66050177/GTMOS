from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.api.routes import products, accounts, drafts, pipeline, analytics

app = FastAPI(
    title="GTMOS API",
    description="AI GTM Command Center API",
    version="0.1.0"
)

app.include_router(products.router)
app.include_router(accounts.router)
app.include_router(drafts.router)
app.include_router(pipeline.router)
app.include_router(analytics.router)

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection check failed: {str(e)}"
        )
