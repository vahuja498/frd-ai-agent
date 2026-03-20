"""
azure_devops_watcher.py

Azure DevOps Watcher — polls every N seconds for work items
tagged with the trigger tag, then auto-generates and posts FRDs.

Run:
  python azure_devops_watcher.py

Make sure your FastAPI server (python run.py) is also running.
"""
import sys
import time
import tempfile
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.azure_devops import AzureDevOpsService


API_BASE = f"http://localhost:{settings.app_port}"


def generate_frd_via_api(
    project_name: str,
    transcript: str = "",
    mom: str = "",
    sow: str = "",
    extras: list[str] = None,
) -> dict | None:
    """Call the local FastAPI /generate-frd endpoint."""
    # Merge all extra docs into SOW if no dedicated sow found
    if not sow and extras:
        sow = "\n\n".join(extras)
    if not transcript and not mom and not sow:
        print("[Watcher] No usable text content found — skipping")
        return None

    payload = {
        "project_name": project_name,
        "transcript":   transcript or "No transcript provided.",
        "mom":          mom or "No MoM provided.",
        "sow":          sow or "No SOW provided.",
    }

    try:
        resp = requests.post(
            f"{API_BASE}/generate-frd",
            json=payload,
            timeout=600,  # Ollama can be slow
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[Watcher] FRD generation API call failed: {e}")
        return None


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def process_work_item(ado: AzureDevOpsService, item: dict) -> None:
    wi_id        = item["id"]
    project_name = item["title"]
    attachments  = item["attachments"]

    print(f"\n[Watcher] Processing: [{wi_id}] {project_name}")
    print(f"[Watcher] Attachments found: {len(attachments)}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Download and classify all attachments
        transcript_texts = []
        mom_texts        = []
        sow_texts        = []
        extra_texts      = []

        for att in attachments:
            filename = att["filename"]
            dest     = tmp / filename
            ok       = ado.download_attachment(att["url"], dest)
            if not ok:
                continue

            # Only read text files — skip images/PDFs for now
            if dest.suffix.lower() in {".txt", ".md", ".csv"}:
                content  = read_text_file(dest)
                doc_type = ado.classify_attachment(filename)
                print(f"[Watcher]   {doc_type:12} ← {filename}")

                if doc_type == "transcript":
                    transcript_texts.append(content)
                elif doc_type == "mom":
                    mom_texts.append(content)
                elif doc_type == "sow":
                    sow_texts.append(content)
                else:
                    extra_texts.append(content)

        # Fall back to work item description if nothing useful attached
        description = item.get("description", "")
        if not any([transcript_texts, mom_texts, sow_texts]) and description:
            print("[Watcher] No text attachments — using work item description as SOW")
            sow_texts.append(description)

        # Generate FRD
        print(f"[Watcher] Calling FRD generator ...")
        result = generate_frd_via_api(
            project_name=project_name,
            transcript="\n\n".join(transcript_texts),
            mom="\n\n".join(mom_texts),
            sow="\n\n".join(sow_texts),
            extras=extra_texts,
        )

        if not result:
            print(f"[Watcher] FRD generation failed for {wi_id}")
            return

        frd_markdown = result.get("frd", "")
        score        = result.get("confidence_score", 0)
        print(f"[Watcher] FRD generated — confidence score: {score}/100")

        # Post comment back to Azure DevOps
        ado.post_frd_comment(wi_id, frd_markdown, score)

        # Upload the saved .md file as attachment
        from pathlib import Path as P
        import re, glob
        slug      = re.sub(r"[^a-zA-Z0-9]+", "_", project_name).strip("_")
        md_files  = sorted(glob.glob(f"output/{slug}_*.md"), reverse=True)
        docx_files = sorted(glob.glob(f"output/{slug}_*.docx"), reverse=True)

        for fpath in (md_files[:1] + docx_files[:1]):
            ado.upload_attachment(wi_id, P(fpath))

        # Mark done — prevents re-processing
        ado.mark_frd_done(wi_id)
        print(f"[Watcher] ✅ Done — work item {wi_id} updated")


def main():
    print("\n" + "="*60)
    print("  Azure DevOps FRD Watcher")
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

    print(f"  Org:         {ado.org}")
    print(f"  Project:     {ado.project}")
    print(f"  Trigger tag: {ado.trigger_tag}")
    print(f"  Done tag:    {ado.done_tag}")
    print(f"  Poll every:  {settings.azure_devops_poll_interval}s")
    print(f"  API:         {API_BASE}")
    print("="*60)
    print("\nWaiting for work items tagged with:", ado.trigger_tag)

    while True:
        try:
            items = ado.get_tagged_work_items()
            if items:
                print(f"\n[Watcher] Found {len(items)} work item(s) to process")
                for item in items:
                    process_work_item(ado, item)
            else:
                print(".", end="", flush=True)  # Heartbeat dot

        except KeyboardInterrupt:
            print("\n\n[Watcher] Stopped.")
            break
        except Exception as e:
            print(f"\n[Watcher] Error: {e}")

        time.sleep(settings.azure_devops_poll_interval)


if __name__ == "__main__":
    main()