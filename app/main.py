"""
app/main.py
FastAPI application factory - optimized for Replit.
Defers LLM initialization to avoid health check timeouts.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import webhook handler
try:
    from webhook_handler import router as webhook_router
except ImportError:
    webhook_router = None

# Global services (lazy loaded)
llm_service = None
vector_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup - skip heavy initialization for health checks"""
    print("\n" + "="*60)
    print("  FRD AI Agent — Starting Up")
    print("="*60)
    print("[Startup] ✓ FastAPI initialized")
    print("[Startup] ✓ Webhooks enabled")
    print("[Startup] ✓ LLM will load on first request")
    print("="*60 + "\n")
    yield
    print("\n[Shutdown] FRD AI Agent stopped.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FRD AI Agent",
        description="AI-powered FRD generator with Azure DevOps webhooks.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    from app.routes.frd_routes import router as frd_router
    app.include_router(frd_router, prefix="")
    
    if webhook_router:
        app.include_router(webhook_router)
    
    @app.get("/", tags=["Root"])
    async def root():
        """Health check - responds instantly"""
        return {
            "status": "ok",
            "message": "FRD AI Agent running",
            "docs": "/docs",
            "webhooks": "enabled" if webhook_router else "disabled"
        }
    
    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint"""
        return {"status": "healthy"}
    
    return app


app = create_app()