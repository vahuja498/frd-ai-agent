# FRD AI Agent

An AI-powered **Functional Requirement Document (FRD) Generator** built with FastAPI, FAISS, Sentence Transformers, and OpenAI (or Grok).

Paste your meeting transcript, MoM, and SOW — get a complete, structured FRD in seconds.

---

## How It Works

```
Your Documents          RAG Knowledge Base
(Transcript + MoM + SOW)   (Past FRDs via FAISS)
        │                        │
        └──────────┬─────────────┘
                   ▼
          LLM + Master Prompt
                   ▼
      Complete FRD (Markdown)
      + Validation Report
      + Confidence Score
```

---

## Quick Start (5 steps)

### 1. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> First run takes ~2 minutes — downloads the embedding model (~90MB).

### 3. Set your API key

```bash
# Copy the example env file
cp .env.example .env
```

Open `.env` and fill in your key:

```env
# For OpenAI (default):
OPENAI_API_KEY=sk-your-key-here
MODEL_PROVIDER=openai

# OR for Grok (xAI):
GROK_API_KEY=your-grok-key-here
MODEL_PROVIDER=grok
```

### 4. Run the server

```bash
python run.py
```

You'll see:
```
==================================================
  FRD AI Agent — Starting Up
==================================================
[VectorStore] Loading embedding model: all-MiniLM-L6-v2
[VectorStore] Indexed 12 chunks from 1 FRD file(s)
[LLMService] Provider: OPENAI | Model: gpt-4o
[Startup] API ready at http://localhost:8000
[Startup] Docs at   http://localhost:8000/docs
==================================================
```

### 5. Test the API

Open your browser: **http://localhost:8000/docs**

Click **POST /generate-frd → Try it out** and paste this example:

```json
{
  "project_name": "Customer Portal v2",
  "transcript": "We need a login page with SSO support using Azure AD...",
  "mom": "Action items: 1. Build login module 2. Integrate with Zendesk...",
  "sow": "Scope: Deliver a web-based customer portal with authentication and invoice management..."
}
```

Or use the **sample files** from `data/sample_inputs/`:

```bash
curl -X POST http://localhost:8000/generate-frd \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Acme Customer Portal",
    "transcript": "'"$(cat data/sample_inputs/transcript.txt)"'",
    "mom": "'"$(cat data/sample_inputs/mom.txt)"'",
    "sow": "'"$(cat data/sample_inputs/sow.txt)"'"
  }'
```

---

## Project Structure

```
frd-ai-agent/
│
├── app/
│   ├── main.py              ← FastAPI app factory + startup
│   ├── config.py            ← All settings (env vars)
│   ├── routes/
│   │   └── frd_routes.py    ← POST /generate-frd, GET /health
│   ├── services/
│   │   ├── ingestion.py     ← Clean + chunk input documents
│   │   ├── vector_store.py  ← FAISS index (local, no API key)
│   │   ├── retriever.py     ← RAG: top-K similar FRD chunks
│   │   ├── llm_service.py   ← OpenAI / Grok client
│   │   ├── frd_generator.py ← Master prompt + FRD generation
│   │   └── validator.py     ← Quality checks + confidence score
│   ├── models/
│   │   └── schemas.py       ← All Pydantic models
│   └── utils/
│       └── file_loader.py   ← File I/O, text cleaning, chunking
│
├── data/
│   ├── sample_inputs/       ← transcript.txt, mom.txt, sow.txt
│   └── frds/                ← Put past FRD .txt files here
│
├── vectorstore/             ← Auto-created; FAISS index stored here
│
├── requirements.txt
├── .env.example
├── run.py                   ← Entry point: python run.py
└── README.md
```

---

## API Reference

### `POST /generate-frd`

**Request body:**
```json
{
  "project_name": "string",
  "transcript":   "string (meeting transcript text)",
  "mom":          "string (minutes of meeting text)",
  "sow":          "string (statement of work text)"
}
```

**Response:**
```json
{
  "project_name":    "string",
  "frd":             "string (full FRD in Markdown)",
  "frd_structured":  null,
  "validation": {
    "issues":                  [...],
    "suggested_improvements":  [...],
    "missing_sections":        [...],
    "total_issues":            0
  },
  "confidence_score":   85,
  "rag_sources_used":   3,
  "model_used":         "openai/gpt-4o"
}
```

### `GET /health`
Returns API status and vector store statistics.

---

## Adding More Historical FRDs

Drop any `.txt` FRD files into `data/frds/` and restart the server.
They will be auto-indexed into the FAISS vector store on startup.

```bash
cp my_old_frd.txt data/frds/
python run.py   # re-indexes automatically
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `MODEL_PROVIDER` | `openai` | `openai` or `grok` |
| `OPENAI_API_KEY` | — | Your OpenAI key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model name |
| `GROK_API_KEY` | — | Your Grok/xAI key |
| `GROK_MODEL` | `grok-beta` | Grok model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `VECTORSTORE_PATH` | `./vectorstore` | Where FAISS index is saved |
| `TOP_K_RESULTS` | `3` | How many past FRDs to retrieve |
| `APP_PORT` | `8000` | Server port |

---

## Troubleshooting

**`ModuleNotFoundError`** → Make sure your virtual environment is activated and `pip install -r requirements.txt` completed.

**`No API key found`** → Copy `.env.example` to `.env` and add your key.

**`FRD is empty or short`** → Your input documents are too short. Provide at least a few sentences per document.

**Slow first startup** → The embedding model downloads once (~90MB). Subsequent starts are fast.
