"""
app/main.py
FastAPI application factory.
Handles startup (vector store indexing) and includes all routes including webhooks.
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.frd_routes import router as frd_router, init_services
from app.services.vector_store import VectorStoreService    
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
    Startup: initialise vector store and LLM service.       
    Index sample FRDs if vector store is empty.
    """
    print("\n" + "="*60)
    print("  FRD AI Agent — Starting Up")
    print("="*60)
    
    # Initialise vector store
    vector_store = VectorStoreService()
    
    # Auto-index FRDs from data/frds/ if store is empty     
    if vector_store.total_chunks == 0:
        frds_dir = Path("data/frds")
        if frds_dir.exists():
            print(f"[Startup] Indexing FRDs from: {frds_dir}")
            count = vector_store.index_frds_from_directory(str(frds_dir))
            print(f"[Startup] Indexed {count} FRD chunks")  
        else:
            print("[Startup] No FRDs directory found — vector store will be empty")
            print("[Startup] Place .txt FRD files in data/frds/ to enable RAG")
    
    # Initialise LLM service
    llm_service = LLMService()
    
    # Inject into routes
    init_services(vector_store, llm_service)
    
    print(f"[Startup] Vector store: {vector_store.total_chunks} chunks ready")
    print(f"[Startup] LLM: {llm_service.model_name}")       
    print("[Startup] API ready at http://localhost:8000")   
    print("[Startup] Docs at   http://localhost:8000/docs")
    
    if webhook_router:
        print("[Startup] Webhooks enabled at /webhooks/*")
    
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
            "a complete structured FRD using RAG + LLM. "
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