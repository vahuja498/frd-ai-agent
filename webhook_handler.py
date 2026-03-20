"""
webhook_handler.py
FastAPI endpoint to receive Azure DevOps webhooks and trigger FRD generation in real-time.
"""
from fastapi import APIRouter, Request, HTTPException
import json
import asyncio
from typing import Optional

from app.services.frd_generator import FRDGeneratorService
from app.services.llm_service import LLMService
from attachment_integration import (
    AzureDevOpsAttachmentFetcher,
    FRDGenerationPipeline,
)
from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def extract_work_item_id(event: dict) -> Optional[int]:
    """Extract work item ID from Azure DevOps webhook payload"""
    try:
        resource = event.get("resource", {})
        return resource.get("id")
    except:
        return None


def has_trigger_tag(event: dict, trigger_tag: str) -> bool:
    """Check if work item has the trigger tag"""
    try:
        fields = event.get("resource", {}).get("fields", {})
        tags = fields.get("System.Tags", "")
        if not tags:
            return False
        tag_list = [t.strip() for t in tags.split(";")]
        return trigger_tag in tag_list
    except:
        return False


async def process_work_item_async(
    wi_id: int,
    org: str,
    project: str,
    pat: str,
    done_tag: str,
):
    """Async task to process work item"""
    try:
        llm = LLMService()
        frd_gen = FRDGeneratorService(llm)
        fetcher = AzureDevOpsAttachmentFetcher(org, project, pat)
        pipeline = FRDGenerationPipeline(fetcher, frd_gen)
        
        success, frd = pipeline.process(wi_id, done_tag=done_tag)
        
        if success:
            print(f"[Webhook] ✅ WI {wi_id} processed successfully")
        else:
            print(f"[Webhook] ❌ WI {wi_id} processing failed")
    except Exception as e:
        print(f"[Webhook] Error processing WI {wi_id}: {e}")


@router.post("/work-item-updated")
async def handle_work_item_updated(request: Request):
    """
    Webhook endpoint for Azure DevOps work item updates.
    
    Setup in Azure DevOps:
    1. Go to Project Settings → Service Hooks
    2. New Subscription → Work item updated
    3. URL: https://your-domain.com/webhooks/work-item-updated
    4. Filters: [Tag] equals [presales]
    """
    try:
        payload = await request.json()
        
        # Extract info
        wi_id = extract_work_item_id(payload)
        event_type = payload.get("eventType", "")
        
        if not wi_id:
            raise HTTPException(status_code=400, detail="No work item ID found")
        
        # Check for trigger tag
        if not has_trigger_tag(payload, settings.azure_devops_trigger_tag):
            print(f"[Webhook] WI {wi_id} — no trigger tag, skipping")
            return {"status": "skipped", "reason": "no trigger tag"}
        
        print(f"[Webhook] ✓ WI {wi_id} updated — processing...")
        
        # Extract org/project from webhook (alt: use settings)
        org = settings.azure_devops_org.replace("https://dev.azure.com/", "")
        project = settings.azure_devops_project
        pat = settings.azure_devops_pat
        done_tag = settings.azure_devops_done_tag
        
        # Fire async task (don't block webhook response)
        asyncio.create_task(
            process_work_item_async(wi_id, org, project, pat, done_tag)
        )
        
        return {
            "status": "queued",
            "work_item_id": wi_id,
            "event": event_type,
        }
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        print(f"[Webhook] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/work-item-tagged")
async def handle_work_item_tagged(request: Request):
    """Alternative: webhook triggered only when tag is added"""
    try:
        payload = await request.json()
        wi_id = extract_work_item_id(payload)
        
        if not wi_id:
            raise HTTPException(status_code=400, detail="No work item ID found")
        
        print(f"[Webhook] ✓ WI {wi_id} tagged — processing...")
        
        org = settings.azure_devops_org.replace("https://dev.azure.com/", "")
        project = settings.azure_devops_project
        pat = settings.azure_devops_pat
        done_tag = settings.azure_devops_done_tag
        
        asyncio.create_task(
            process_work_item_async(wi_id, org, project, pat, done_tag)
        )
        
        return {
            "status": "queued",
            "work_item_id": wi_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "webhook": "listening"}