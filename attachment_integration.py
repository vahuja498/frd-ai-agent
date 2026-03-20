"""
attachment_integration.py
Bridge between Azure DevOps attachments and FRD generation service.
"""
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import requests
from urllib.parse import quote

from app.services.azure_devops import AzureDevOpsService
from app.services.frd_generator import FRDGeneratorService
from app.services.llm_service import LLMService


class AttachmentProcessor:
    """Download, classify, and process Azure DevOps attachments"""
    
    DOCUMENT_TYPES = {
        "transcript": ["transcript", "call", "recording", "meeting_notes"],
        "mom": ["mom", "minutes", "meeting"],
        "sow": ["sow", "scope", "statement_of_work", "requirements"],
    }
    
    @staticmethod
    def classify_document(filename: str) -> str:
        """Classify document by filename"""
        lower = filename.lower()
        
        for doc_type, keywords in AttachmentProcessor.DOCUMENT_TYPES.items():
            if any(kw in lower for kw in keywords):
                return doc_type
        
        return "other"
    
    @staticmethod
    def read_text_file(path: Path) -> str:
        """Safe text file reading"""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return ""


class AzureDevOpsAttachmentFetcher:
    """Fetch attachments from Azure DevOps work items"""
    
    def __init__(self, org: str, project: str, pat: str):
        self.org = org
        self.project = project
        self.pat = pat
        self.base_url = f"https://dev.azure.com/{org}/{quote(project)}"
        self.auth = ("", pat)
    
    def get_work_item(self, wi_id: int) -> Dict:
        """Fetch work item with all attachment metadata"""
        resp = requests.get(
            f"{self.base_url}/_apis/wit/workitems/{wi_id}?api-version=7.0",
            auth=self.auth,
        )
        resp.raise_for_status()
        data = resp.json()
        
        attachments = []
        if "relations" in data:
            for rel in data["relations"]:
                if rel["rel"] == "AttachedFile":
                    att_resp = requests.get(rel["url"], auth=self.auth)
                    att_resp.raise_for_status()
                    att_info = att_resp.json()
                    attachments.append({
                        "filename": att_info.get("fileName"),
                        "url": att_info.get("url"),
                        "size": att_info.get("size"),
                    })
        
        return {
            "id": wi_id,
            "title": data["fields"].get("System.Title"),
            "description": data["fields"].get("System.Description", ""),
            "attachments": attachments,
        }
    
    def download_attachment(self, url: str, dest_path: Path) -> bool:
        """Download attachment file"""
        try:
            resp = requests.get(url, auth=self.auth)
            resp.raise_for_status()
            dest_path.write_bytes(resp.content)
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def upload_attachment(self, wi_id: int, file_path: Path) -> bool:
        """Upload file as attachment to work item"""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            filename = file_path.name
            resp = requests.post(
                f"{self.base_url}/_apis/wit/attachments?fileName={quote(filename)}&api-version=7.0",
                data=content,
                headers={"Content-Type": "application/octet-stream"},
                auth=self.auth,
            )
            resp.raise_for_status()
            att_data = resp.json()
            
            # Link to work item
            patch_resp = requests.patch(
                f"{self.base_url}/_apis/wit/workitems/{wi_id}?api-version=7.0",
                json=[{
                    "op": "add",
                    "path": "/relations/-",
                    "value": {"rel": "AttachedFile", "url": att_data["url"]},
                }],
                headers={"Content-Type": "application/json-patch+json"},
                auth=self.auth,
            )
            patch_resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Upload failed: {e}")
            return False
    
    def add_tag(self, wi_id: int, tag: str) -> bool:
        """Add tag to work item"""
        try:
            # Get current tags
            wi = self.get_work_item(wi_id)
            current_tags = wi.get("tags", "")
            
            # Add new tag if not present
            tags_list = [t.strip() for t in current_tags.split(";") if t.strip()]
            if tag not in tags_list:
                tags_list.append(tag)
            new_tags = ";".join(tags_list)
            
            resp = requests.patch(
                f"{self.base_url}/_apis/wit/workitems/{wi_id}?api-version=7.0",
                json=[{
                    "op": "replace",
                    "path": "/fields/System.Tags",
                    "value": new_tags,
                }],
                headers={"Content-Type": "application/json-patch+json"},
                auth=self.auth,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Tag update failed: {e}")
            return False


class DocumentCombiner:
    """Combine classified documents into input for FRD generator"""
    
    @staticmethod
    def combine(
        transcripts: List[str],
        moms: List[str],
        sows: List[str],
        description: str = "",
    ) -> str:
        """Combine all documents into structured input"""
        sections = []
        
        if transcripts:
            sections.append("## Transcripts\n" + "\n---\n".join(transcripts))
        
        if moms:
            sections.append("## Minutes of Meeting\n" + "\n---\n".join(moms))
        
        if sows:
            sections.append("## Statement of Work / Requirements\n" + "\n---\n".join(sows))
        
        if description:
            sections.append(f"## Work Item Description\n{description}")
        
        return "\n\n".join(sections)


class FRDGenerationPipeline:
    """End-to-end FRD generation from Azure DevOps work item
    
    USAGE IN WATCHER:
    ─────────────────
    from attachment_integration import (
        AzureDevOpsAttachmentFetcher,
        FRDGenerationPipeline,
    )
    from app.services.frd_generator import FRDGeneratorService
    from app.services.llm_service import LLMService
    
    # In your process_work_item function:
    llm = LLMService()
    frd_gen = FRDGeneratorService(llm)
    fetcher = AzureDevOpsAttachmentFetcher(org, project, pat)
    pipeline = FRDGenerationPipeline(fetcher, frd_gen)
    success, frd_content = pipeline.process(wi_id, done_tag)
    """
    
    def __init__(
        self,
        fetcher: AzureDevOpsAttachmentFetcher,
        frd_generator: FRDGeneratorService,
        rag_service: Optional[RAGService] = None,
    ):
        self.fetcher = fetcher
        self.frd_generator = frd_generator
        self.rag_service = rag_service
    
    def process(
        self,
        wi_id: int,
        done_tag: str = "frd-generated",
    ) -> Tuple[bool, str]:
        """
        Process work item: fetch attachments → generate FRD → upload.
        Returns (success, frd_content)
        """
        print(f"\n[Pipeline] Processing WI {wi_id}...")
        
        try:
            # Fetch work item
            wi = self.fetcher.get_work_item(wi_id)
            project_name = wi["title"]
            print(f"  Title: {project_name}")
            print(f"  Attachments: {len(wi['attachments'])}")
            
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                
                # Download and classify
                transcripts = []
                moms = []
                sows = []
                
                for att in wi["attachments"]:
                    dest = tmp / att["filename"]
                    if not self.fetcher.download_attachment(att["url"], dest):
                        continue
                    
                    if dest.suffix.lower() in {".txt", ".md", ".csv"}:
                        content = AttachmentProcessor.read_text_file(dest)
                        doc_type = AttachmentProcessor.classify_document(att["filename"])
                        print(f"    {doc_type:12} ← {att['filename']}")
                        
                        if doc_type == "transcript":
                            transcripts.append(content)
                        elif doc_type == "mom":
                            moms.append(content)
                        elif doc_type == "sow":
                            sows.append(content)
                
                # Fallback to description
                if not any([transcripts, moms, sows]) and wi["description"]:
                    print("  No text attachments — using work item description")
                    sows.append(wi["description"])
                
                if not any([transcripts, moms, sows]):
                    print("  ⚠️  No usable content found")
                    return False, ""
                
                # Combine documents
                combined = DocumentCombiner.combine(
                    transcripts, moms, sows, wi["description"]
                )
                
                # Get RAG context if available
                rag_context = ""
                if self.rag_service:
                    rag_context = self.rag_service.retrieve(project_name, combined)
                
                # Generate FRD
                print("  Generating FRD...")
                frd_content = self.frd_generator.generate(
                    project_name=project_name,
                    combined_input=combined,
                    rag_context=rag_context,
                )
                
                print(f"  Generated {len(frd_content)} chars")
                
                # Save and upload
                frd_path = tmp / f"FRD_{wi_id}.md"
                frd_path.write_text(frd_content)
                
                if self.fetcher.upload_attachment(wi_id, frd_path):
                    print(f"  ✓ Uploaded FRD")
                
                # Mark done
                if self.fetcher.add_tag(wi_id, done_tag):
                    print(f"  ✓ Tagged '{done_tag}'")
                
                return True, frd_content
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False, ""