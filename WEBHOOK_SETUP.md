# Azure DevOps Webhook Setup Guide

## Quick Start

### 1. Update your FastAPI app (main.py or run.py)

```python
from fastapi import FastAPI
from webhook_handler import router as webhook_router

app = FastAPI()

# Add webhook routes
app.include_router(webhook_router)

# Your other routes...
```

### 2. Expose your FastAPI app to the internet

Azure DevOps webhooks need a public URL. Options:

**Option A: ngrok (for local testing)**
```bash
# Terminal 1: Start your FastAPI app
python run.py

# Terminal 2: Create tunnel
ngrok http 8000
# Output: https://abc123.ngrok.io
```

**Option B: Deploy to cloud**
- Azure App Service
- Heroku
- Railway.app
- AWS Lambda

**Option C: Use ngrok Python**
```bash
pip install pyngrok
python -c "from pyngrok import ngrok; print(ngrok.connect(8000))"
```

### 3. Create Service Hook in Azure DevOps

1. Go to: **Project Settings** → **Service Hooks**
2. Click **+ Create subscription**
3. Select **Work item updated**
4. Click **Next**
5. **URL:** `https://your-public-url/webhooks/work-item-updated`
   - Example: `https://abc123.ngrok.io/webhooks/work-item-updated`
6. **Filters:**
   - Event type: Work item updated
   - (Optional) Add filter: **[Tag] equals [presales]**
7. Click **Finish**

### 4. Test the Webhook

**Method 1: Tag a work item in Azure DevOps**
1. Open work item [743] or [675]
2. Add tag `presales` (or your trigger tag)
3. Watch your FastAPI logs for real-time processing

**Method 2: Manual curl test**
```bash
curl -X POST https://your-public-url/webhooks/work-item-updated \
  -H "Content-Type: application/json" \
  -d '{
    "resource": {
      "id": 743,
      "fields": {
        "System.Tags": "presales",
        "System.Title": "New SOW"
      }
    }
  }'
```

**Check health:**
```bash
curl https://your-public-url/webhooks/health
# Response: {"status":"ok","webhook":"listening"}
```

---

## How It Works

1. **User tags work item** in Azure DevOps with "presales"
2. **Azure DevOps sends webhook** to your FastAPI endpoint
3. **Webhook handler extracts** work item ID & checks trigger tag
4. **Async task fires** to process immediately (non-blocking)
5. **FRD generated** using your LLM service
6. **FRD attached** back to work item
7. **Done tag added** to prevent re-processing

---

## Environment Setup

Add to your `.env`:

```env
# Webhook config
WEBHOOK_SECRET=optional-secret-key

# Azure DevOps (should already be set)
AZURE_DEVOPS_ORG=https://dev.azure.com/Dynamicssmartz
AZURE_DEVOPS_PROJECT=Internal CRM
AZURE_DEVOPS_PAT=your-pat-token
AZURE_DEVOPS_TRIGGER_TAG=presales
AZURE_DEVOPS_DONE_TAG=presales

# FastAPI
APP_PORT=8000
```

---

## Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/webhooks/work-item-updated` | Main webhook for any WI update |
| POST | `/webhooks/work-item-tagged` | Alternative: only tag changes |
| GET | `/webhooks/health` | Health check |

---

## Debugging

**Check FastAPI logs:**
```
[Webhook] ✓ WI 743 updated — processing...
[Pipeline] Processing WI 743...
[FRDGenerator] Calling LLM for project: New SOW
[Webhook] ✅ WI 743 processed successfully
```

**Common issues:**

| Issue | Fix |
|-------|-----|
| 404 Not Found | Ensure webhook URL is correct and app is running |
| Timeout | LLM generation takes time; webhook response is async |
| Tag not detected | Check tag format in Azure DevOps (case-sensitive?) |
| PAT invalid | Refresh Azure DevOps PAT in settings |

---

## Optional: Webhook Signature Verification

Add to webhook_handler.py for security:

```python
import hmac
import hashlib

WEBHOOK_SECRET = settings.webhook_secret  # Set in .env

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@router.post("/work-item-updated")
async def handle_work_item_updated(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature")
    
    if not verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    # ... rest of handler
```

---

## Next Steps

1. Copy `webhook_handler.py` to your project
2. Update your FastAPI app to include webhook routes
3. Deploy to public URL (ngrok for testing)
4. Create Service Hook in Azure DevOps
5. Test by tagging a work item
6. Monitor logs for real-time FRD generation

**Stop polling watcher** (azure_devops_watcher_v2.py) once webhooks are confirmed working.
