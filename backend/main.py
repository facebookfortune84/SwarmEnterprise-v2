import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.webhooks import router as webhook_router
from backend.api.routes import router as core_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SwarmOS")

app = FastAPI(title="SwarmOS Sovereign Factory", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router)
app.include_router(webhook_router)

# Ensure output directory exists for static files
os.makedirs("/mnt/c/SwarmEnterprise_v2/output/src", exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "version": "2.0.0", "engine": "SwarmOS"}
