"""
Example: Adding webhook handler to your FastAPI app
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webhook_handler import router as webhook_router
from app.config import settings

app = FastAPI(
    title="FRD AI Agent",
    description="Automated FRD generation from Azure DevOps",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include webhook routes
app.include_router(webhook_router)

# Your existing routes...
@app.get("/")
def read_root():
    return {"message": "FRD AI Agent running"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.app_port,
    )
