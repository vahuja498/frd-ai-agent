"""
app/services/validator.py
Validates the generated FRD Markdown for completeness, clarity, and quality.
Returns a ValidationReport and a confidence score (0-100).
"""
import re
from typing import List, Tuple

from app.models.schemas import ValidationReport, ValidationIssue

# All required sections that must be present in a valid FRD
REQUIRED_SECTIONS = [
    "Business Objective",
    "Scope",
    "Stakeholders",
    "Assumptions",
    "Dependencies",
    "Functional Requirements",
    "Non-Functional Requirements",
    "Business Rules",
    "Process Flow",
    "Edge Cases",
    "Risks",
    "Open Questions",
]

# Vague words that trigger an ambiguity warning
VAGUE_TERMS = [
    "user-friendly", "fast", "secure", "scalable", "easy to use",
    "robust", "flexible", "modern", "intuitive", "seamless", "efficient",
    "good performance", "high quality",
]


class ValidatorService:
    """
    Analyses the generated FRD Markdown and produces a ValidationReport
    plus a confidence score.
    """

    def validate(self, frd_markdown: str) -> Tuple[ValidationReport, int]:
        """
        Run all checks and return (ValidationReport, confidence_score).
        confidence_score is 0-100.
        """
        issues: List[ValidationIssue] = []
        missing_sections: List[str] = []
        suggestions: List[str] = []

        # 1 — Check all required sections are present
        for section in REQUIRED_SECTIONS:
            if not self._section_present(frd_markdown, section):
                missing_sections.append(section)
                issues.append(ValidationIssue(
                    severity="Critical",
                    location=f"Section: {section}",
                    detail=f"Required section '{section}' is missing from the FRD.",
                ))

        # 2 — Check for vague/ambiguous language
        for term in VAGUE_TERMS:
            if term.lower() in frd_markdown.lower():
                issues.append(ValidationIssue(
                    severity="Medium",
                    location="Functional / Non-Functional Requirements",
                    detail=f"Vague term detected: '{term}'. Replace with a measurable criterion.",
                ))

        # 3 — Check FR count (warn if very few)
        fr_count = len(re.findall(r"FR-\d+", frd_markdown))
        if fr_count == 0:
            issues.append(ValidationIssue(
                severity="Critical",
                location="Section: Functional Requirements",
                detail="No Functional Requirements (FR-XX) found in the document.",
            ))
        elif fr_count < 3:
            issues.append(ValidationIssue(
                severity="High",
                location="Section: Functional Requirements",
                detail=f"Only {fr_count} FR(s) found. Most projects require at least 5-10 FRs.",
            ))
            suggestions.append("Expand the Functional Requirements section with more detailed requirements.")

        # 4 — Check NFR count
        nfr_count = len(re.findall(r"NFR-\d+", frd_markdown))
        if nfr_count == 0:
            issues.append(ValidationIssue(
                severity="High",
                location="Section: Non-Functional Requirements",
                detail="No Non-Functional Requirements (NFR-XX) found.",
            ))
            suggestions.append("Add NFRs covering at least: Performance, Security, Availability.")

        # 5 — Check for INFERRED markers
        inferred_count = frd_markdown.count("[INFERRED]")
        if inferred_count > 0:
            suggestions.append(
                f"{inferred_count} requirement(s) marked [INFERRED]. "
                "Confirm these with the client before sign-off."
            )

        # 6 — Check Open Questions exist
        if "Open Questions" in frd_markdown:
            oq_count = len(re.findall(r"OQ-\d+", frd_markdown))
            if oq_count == 0:
                suggestions.append("Add specific Open Questions (OQ-01, OQ-02...) for client review.")

        # 7 — Check for acceptance criteria
        ac_count = frd_markdown.lower().count("acceptance criteria")
        if ac_count < fr_count and fr_count > 0:
            issues.append(ValidationIssue(
                severity="High",
                location="Section: Functional Requirements",
                detail="Some Functional Requirements are missing Acceptance Criteria.",
            ))

        # 8 — Generate improvement suggestions
        if missing_sections:
            suggestions.insert(0, f"Add the following missing sections: {', '.join(missing_sections)}")

        if not suggestions:
            suggestions.append("FRD looks complete. Perform a manual review before client delivery.")

        # ── Confidence Score ────────────────────────────────────────────────
        score = self._calculate_score(issues, missing_sections, fr_count, nfr_count, frd_markdown)

        report = ValidationReport(
            issues=issues,
            suggested_improvements=suggestions,
            missing_sections=missing_sections,
            total_issues=len(issues),
        )

        return report, score

    # ── Private ───────────────────────────────────────────────────────────────

    def _section_present(self, text: str, section_name: str) -> bool:
        """Check if a section heading appears in the Markdown."""
        pattern = rf"#+\s+.*{re.escape(section_name)}.*"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _calculate_score(
        self,
        issues: List[ValidationIssue],
        missing_sections: List[str],
        fr_count: int,
        nfr_count: int,
        frd_text: str,
    ) -> int:
        score = 100

        # Deduct for missing sections
        score -= len(missing_sections) * 8

        # Deduct for issues by severity
        for issue in issues:
            if issue.severity == "Critical":
                score -= 15
            elif issue.severity == "High":
                score -= 8
            elif issue.severity == "Medium":
                score -= 3
            elif issue.severity == "Low":
                score -= 1

        # Bonus for richness
        if fr_count >= 5:
            score += 5
        if nfr_count >= 3:
            score += 3
        if "acceptance criteria" in frd_text.lower():
            score += 5

        return max(0, min(100, score))
