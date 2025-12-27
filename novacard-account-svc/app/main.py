from fastapi import FastAPI
from app.db import connect_db, close_db
from app.routes.accounts import router as accounts_router

app = FastAPI(title="NovaCard Account Service", version="0.1.0")

@app.on_event("startup")
async def _startup():
    await connect_db()

@app.on_event("shutdown")
async def _shutdown():
    await close_db()

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(accounts_router)