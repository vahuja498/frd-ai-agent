"""
app/models/schemas.py
All Pydantic request/response models for the FRD AI Agent API.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


# ── Request ───────────────────────────────────────────────────────────────────

class FRDRequest(BaseModel):
    """Input payload for FRD generation."""
    transcript: str = Field(
        ...,
        description="Raw meeting transcript text",
        min_length=20,
    )
    mom: str = Field(
        ...,
        description="Minutes of Meeting text",
        min_length=20,
    )
    sow: str = Field(
        ...,
        description="Statement of Work / Proposal text",
        min_length=20,
    )
    project_name: Optional[str] = Field(
        default="Unnamed Project",
        description="Project name for the FRD header",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "project_name": "Customer Portal v2",
                "transcript": "John: We need a login page with SSO support...",
                "mom": "Action items: 1. Build login module 2. Integrate with Azure AD...",
                "sow": "Scope: Deliver a web-based customer portal with authentication...",
            }
        }
    }


# ── Internal ──────────────────────────────────────────────────────────────────

class DocumentChunk(BaseModel):
    """A single chunk of processed text with metadata."""
    text: str
    source: str
    chunk_index: int


class RetrievedFRD(BaseModel):
    """A retrieved past FRD chunk from the vector store."""
    text: str
    source: str
    similarity_score: float


# ── FRD Structure ─────────────────────────────────────────────────────────────

class FunctionalRequirement(BaseModel):
    id: str
    title: str
    description: str
    actor: str
    priority: str
    acceptance_criteria: List[str]
    source: str = Field(description="Explicit | Inferred")


class NonFunctionalRequirement(BaseModel):
    id: str
    category: str
    description: str
    metric: str


class Risk(BaseModel):
    id: str
    description: str
    likelihood: str
    impact: str
    mitigation: str


class OpenQuestion(BaseModel):
    id: str
    question: str
    status: str = "Open"


class FRDDocument(BaseModel):
    """Fully structured FRD."""
    project_name: str
    version: str = "1.0"
    date: str
    business_objective: str
    scope_in: List[str]
    scope_out: List[str]
    stakeholders: List[dict]
    assumptions: List[str]
    dependencies: List[str]
    functional_requirements: List[FunctionalRequirement]
    non_functional_requirements: List[NonFunctionalRequirement]
    business_rules: List[str]
    process_flow: List[dict]
    edge_cases: List[dict]
    risks: List[Risk]
    open_questions: List[OpenQuestion]
    raw_markdown: str = Field(description="Full FRD as Markdown string")


# ── Validation ────────────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    severity: str = Field(description="Critical | High | Medium | Low")
    location: str
    detail: str


class ValidationReport(BaseModel):
    issues: List[ValidationIssue]
    suggested_improvements: List[str]
    missing_sections: List[str]
    total_issues: int


# ── Response ──────────────────────────────────────────────────────────────────

class FRDResponse(BaseModel):
    """Final API response."""
    project_name: str
    frd: str = Field(description="Complete FRD in Markdown format")
    frd_structured: Optional[dict] = Field(
        default=None,
        description="Structured JSON representation of the FRD",
    )
    validation: ValidationReport
    confidence_score: int = Field(ge=0, le=100, description="0–100 quality score")
    rag_sources_used: int = Field(description="Number of past FRDs used as context")
    model_used: str


class HealthResponse(BaseModel):
    status: str
    vectorstore_loaded: bool
    frd_count: int
    model_provider: str
