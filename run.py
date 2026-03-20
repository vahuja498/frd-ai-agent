"""
run.py
Single-file entry point.
Run: python run.py
"""
import sys
from pathlib import Path

# Ensure the project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from app.config import settings


def main():
    # Ollama runs locally — no API key needed
    if settings.model_provider != "ollama" and not settings.active_api_key:
        provider = settings.model_provider.upper()
        key_name = "OPENAI_API_KEY" if settings.model_provider == "openai" else "GROK_API_KEY"
        print(f"\n{'='*60}")
        print(f"  ERROR: No API key found for {provider}.")
        print(f"  Set {key_name} in your .env file.")
        print(f"  Copy .env.example → .env and add your key.")
        print(f"{'='*60}\n")
        sys.exit(1)

    print(f"\n[Config] Provider : {settings.model_provider.upper()}")
    print(f"[Config] Model    : {settings.active_model}")
    if settings.model_provider == "ollama":
        print(f"[Config] Ollama   : {settings.ollama_base_url}")

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()