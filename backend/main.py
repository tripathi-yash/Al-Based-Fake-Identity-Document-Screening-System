"""
FastAPI entrypoint. Run with: uvicorn main:app --reload
"""
from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="AI-Based Fake Identity & Document Screening System")

app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
