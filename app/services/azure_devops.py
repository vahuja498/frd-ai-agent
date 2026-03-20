"""
app/services/azure_devops.py

Azure DevOps Integration Service
──────────────────────────────────
Polls Azure DevOps for work items tagged with a specific tag.
When found:
  1. Downloads all attachments
  2. Runs the FRD generation pipeline
  3. Posts the FRD back as a comment + attachment
  4. Updates the work item tag to mark FRD as generated
"""
import os
import time
import tempfile
import requests
from pathlib import Path
from requests.auth import HTTPBasicAuth
from typing import Optional
from datetime import date

from app.config import settings


class AzureDevOpsService:

    def __init__(self):
        self.org        = settings.azure_devops_org
        self.project    = settings.azure_devops_project
        self.pat        = settings.azure_devops_pat
        self.trigger_tag = settings.azure_devops_trigger_tag
        self.done_tag    = settings.azure_devops_done_tag
        self.auth        = HTTPBasicAuth("", self.pat)
        self.base        = f"{self.org}/{self.project}/_apis"
        self._processed  = set()   # in-memory; prevents re-processing

    def is_configured(self) -> bool:
        return all([self.org, self.project, self.pat])

    # ── Polling ───────────────────────────────────────────────────────────────

    def get_tagged_work_items(self) -> list[dict]:
        """
        Query for work items that have the trigger tag and
        have NOT yet been processed (no done_tag).
        """
        wiql = {
            "query": f"""
                SELECT [System.Id], [System.Title], [System.Tags],
                       [System.WorkItemType], [System.State]
                FROM WorkItems
                WHERE [System.TeamProject] = '{self.project}'
                  AND [System.Tags] CONTAINS '{self.trigger_tag}'
                  AND [System.Tags] NOT CONTAINS '{self.done_tag}'
                ORDER BY [System.CreatedDate] DESC
            """
        }
        try:
            resp = requests.post(
                f"{self.base}/wit/wiql?api-version=7.1",
                json=wiql,
                auth=self.auth,
                timeout=15,
            )
            resp.raise_for_status()
            items = resp.json().get("workItems", [])
            result = []
            for item in items:
                wi_id = str(item["id"])
                if wi_id not in self._processed:
                    detail = self._get_work_item(wi_id)
                    if detail:
                        result.append(detail)
            return result
        except Exception as e:
            print(f"[AzureDevOps] Query failed: {e}")
            return []

    def _get_work_item(self, wi_id: str) -> Optional[dict]:
        """Fetch full work item details including relations (for attachments)."""
        try:
            resp = requests.get(
                f"{self.base}/wit/workitems/{wi_id}"
                "?$expand=relations&api-version=7.1",
                auth=self.auth,
                timeout=10,
            )
            resp.raise_for_status()
            data   = resp.json()
            fields = data.get("fields", {})
            rels   = data.get("relations", []) or []

            attachments = [
                {
                    "url":      r["url"],
                    "filename": r.get("attributes", {}).get("name", "attachment"),
                }
                for r in rels
                if r.get("rel") == "AttachedFile"
            ]

            return {
                "id":          wi_id,
                "title":       fields.get("System.Title", f"Work Item {wi_id}"),
                "description": fields.get("System.Description", ""),
                "type":        fields.get("System.WorkItemType", ""),
                "state":       fields.get("System.State", ""),
                "tags":        fields.get("System.Tags", ""),
                "attachments": attachments,
            }
        except Exception as e:
            print(f"[AzureDevOps] Failed to fetch work item {wi_id}: {e}")
            return None

    # ── Attachments ───────────────────────────────────────────────────────────

    def download_attachment(self, url: str, dest: Path) -> bool:
        """Download a single attachment to dest path."""
        try:
            resp = requests.get(url, auth=self.auth, timeout=60, stream=True)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            return True
        except Exception as e:
            print(f"[AzureDevOps] Download failed ({url}): {e}")
            return False

    def classify_attachment(self, filename: str) -> str:
        """
        Guess document type from filename.
        Returns: transcript | mom | sow | presales
        """
        name = filename.lower()
        if any(k in name for k in ["transcript", "meeting_notes", "minutes_raw"]):
            return "transcript"
        if any(k in name for k in ["mom", "minutes", "mot"]):
            return "mom"
        if any(k in name for k in ["sow", "proposal", "scope", "contract"]):
            return "sow"
        return "presales"

    # ── Post back ─────────────────────────────────────────────────────────────

    def post_frd_comment(self, wi_id: str, frd_markdown: str, score: int) -> bool:
        """Post the FRD as a comment on the work item."""
        try:
            comment = (
                f"## FRD Auto-Generated ✅\n\n"
                f"**Confidence Score:** {score}/100  \n"
                f"**Generated:** {date.today().isoformat()}  \n\n"
                f"---\n\n"
                f"{frd_markdown[:3000]}"
                f"\n\n_Full FRD attached as file._"
            )
            resp = requests.post(
                f"{self.base}/wit/workitems/{wi_id}/comments"
                "?api-version=7.1-preview.3",
                json={"text": comment},
                auth=self.auth,
                timeout=15,
            )
            resp.raise_for_status()
            print(f"[AzureDevOps] Comment posted on work item {wi_id}")
            return True
        except Exception as e:
            print(f"[AzureDevOps] Failed to post comment: {e}")
            return False

    def upload_attachment(self, wi_id: str, file_path: Path) -> bool:
        """Upload a file as an attachment to the work item."""
        try:
            # Step 1: Upload the file bytes
            with open(file_path, "rb") as f:
                upload_resp = requests.post(
                    f"{self.base}/wit/attachments"
                    f"?fileName={file_path.name}&api-version=7.1",
                    data=f.read(),
                    auth=self.auth,
                    headers={"Content-Type": "application/octet-stream"},
                    timeout=30,
                )
            upload_resp.raise_for_status()
            attachment_url = upload_resp.json()["url"]

            # Step 2: Link attachment to work item
            patch = [
                {
                    "op":    "add",
                    "path":  "/relations/-",
                    "value": {
                        "rel":        "AttachedFile",
                        "url":        attachment_url,
                        "attributes": {"comment": "FRD generated by AI Agent"},
                    },
                }
            ]
            link_resp = requests.patch(
                f"{self.base}/wit/workitems/{wi_id}?api-version=7.1",
                json=patch,
                auth=self.auth,
                headers={"Content-Type": "application/json-patch+json"},
                timeout=15,
            )
            link_resp.raise_for_status()
            print(f"[AzureDevOps] Attachment uploaded to work item {wi_id}")
            return True
        except Exception as e:
            print(f"[AzureDevOps] Attachment upload failed: {e}")
            return False

    def mark_frd_done(self, wi_id: str) -> bool:
        """
        Add the done_tag to the work item so it won't be re-processed.
        Appends to existing tags rather than replacing them.
        """
        try:
            # Get current tags first
            item = self._get_work_item(wi_id)
            current_tags = item["tags"] if item else ""
            new_tags = f"{current_tags}; {self.done_tag}".strip("; ")

            patch = [{"op": "replace", "path": "/fields/System.Tags", "value": new_tags}]
            resp  = requests.patch(
                f"{self.base}/wit/workitems/{wi_id}?api-version=7.1",
                json=patch,
                auth=self.auth,
                headers={"Content-Type": "application/json-patch+json"},
                timeout=15,
            )
            resp.raise_for_status()
            self._processed.add(wi_id)
            print(f"[AzureDevOps] Work item {wi_id} marked as done (tag: {self.done_tag})")
            return True
        except Exception as e:
            print(f"[AzureDevOps] Failed to mark done: {e}")
            return False