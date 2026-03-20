"""
app/main.py
FastAPI application factory.
Handles startup (vector store indexing) and includes all routes including webhooks.
Optimized for Replit: Vector store disabled to avoid HuggingFace rate limiting.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.frd_routes import router as frd_router, init_services
from app.services.llm_service import LLMService

# Import webhook handler
try:
    from webhook_handler import router as webhook_router
except ImportError:
    print("[WARNING] webhook_handler not found — webhooks disabled")
    webhook_router = None

# ─────────────────────────────────────────────────────────────────────────────
# App Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: initialise LLM service.
    Vector store disabled for Replit (HuggingFace rate limiting).
    """
    print("\n" + "="*60)
    print("  FRD AI Agent — Starting Up")
    print("="*60)
    
    # Disable vector store for Replit testing (HuggingFace rate limits)
    print("[Startup] Vector store: DISABLED (Replit mode)")
    print("[Startup] RAG functionality: Limited")
    vector_store = None
    
    # Initialise LLM service
    llm_service = LLMService()
    
    # Inject into routes (vector_store=None means RAG disabled)
    init_services(vector_store, llm_service)
    
    print(f"[Startup] LLM: {llm_service.model_name}")       
    print("[Startup] API ready at http://localhost:8000")   
    print("[Startup] Docs at   http://localhost:8000/docs")
    
    if webhook_router:
        print("[Startup] ✓ Webhooks enabled at /webhooks/*")
    
    print("="*60 + "\n")
    yield
    print("\n[Shutdown] FRD AI Agent stopped.")


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="FRD AI Agent",
        description=(
            "AI-powered Functional Requirement Document generator. "
            "Upload project documents (transcript, MoM, SOW) and receive "
            "a complete structured FRD using LLM. "
            "Integrates with Azure DevOps for real-time FRD generation via webhooks."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS – allow all origins for local development      
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(frd_router, prefix="")
    
    # Include webhook router if available
    if webhook_router:
        app.include_router(webhook_router)
    
    @app.get("/", tags=["Root"])
    async def root():
        endpoints = {
            "message": "FRD AI Agent is running",
            "docs": "http://localhost:8000/docs",
            "generate": "POST http://localhost:8000/generate-frd",
        }
        if webhook_router:
            endpoints["webhooks"] = {
                "work-item-updated": "POST /webhooks/work-item-updated",
                "health": "GET /webhooks/health",
            }
        return endpoints
    
    return app


app = create_app()