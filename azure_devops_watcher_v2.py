"""
azure_devops_watcher_v2.py
Enhanced watcher using FRDGenerationPipeline
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.azure_devops import AzureDevOpsService
from app.services.frd_generator import FRDGeneratorService
from app.services.llm_service import LLMService
from attachment_integration import (
    AzureDevOpsAttachmentFetcher,
    FRDGenerationPipeline,
)


def main():
    print("\n" + "="*60)
    print("  Azure DevOps FRD Watcher v2")
    print("="*60)
    
    ado = AzureDevOpsService()
    
    if not ado.is_configured():
        print("\n[ERROR] Azure DevOps not configured.")
        print("Set these in your .env file:")
        print("  AZURE_DEVOPS_ORG=https://dev.azure.com/yourorg")
        print("  AZURE_DEVOPS_PROJECT=YourProject")
        print("  AZURE_DEVOPS_PAT=your-personal-access-token")
        print("  AZURE_DEVOPS_TRIGGER_TAG=generate-frd")
        print("  AZURE_DEVOPS_DONE_TAG=frd-generated")
        sys.exit(1)
    
    # Extract org name from URL
    org = ado.org.replace("https://dev.azure.com/", "")
    
    print(f"  Org:         {ado.org}")
    print(f"  Project:     {ado.project}")
    print(f"  Trigger tag: {ado.trigger_tag}")
    print(f"  Done tag:    {ado.done_tag}")
    print(f"  Poll every:  {settings.azure_devops_poll_interval}s")
    print("="*60)
    
    # Initialize pipeline
    llm = LLMService()
    frd_generator = FRDGeneratorService(llm)
    fetcher = AzureDevOpsAttachmentFetcher(org, ado.project, ado.pat)
    pipeline = FRDGenerationPipeline(fetcher, frd_generator)
    
    print(f"\nWaiting for work items tagged with: {ado.trigger_tag}")
    
    while True:
        try:
            items = ado.get_tagged_work_items()
            if items:
                print(f"\n[Watcher] Found {len(items)} work item(s) to process")
                for item in items:
                    success, frd = pipeline.process(
                        item["id"],
                        done_tag=ado.done_tag
                    )
                    if success:
                        print(f"[Watcher] ✅ WI {item['id']} completed")
                    else:
                        print(f"[Watcher] ❌ WI {item['id']} failed")
            else:
                print(".", end="", flush=True)
        
        except KeyboardInterrupt:
            print("\n\n[Watcher] Stopped.")
            break
        except Exception as e:
            print(f"\n[Watcher] Error: {e}")
        
        time.sleep(settings.azure_devops_poll_interval)


if __name__ == "__main__":
    main()