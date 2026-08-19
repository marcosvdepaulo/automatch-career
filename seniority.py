"""Seniority normalization and eligibility policy, independent of scoring weights."""

import re

from domain.models import (
    CandidateSeniority,
    OpportunitySeniority,
    SeniorityCompatibility,
    SeniorityLevel,
)


SENIORITY_ALIASES = {
    SeniorityLevel.INTERN: ("intern", "internship", "estágio", "estagio", "estagiário", "estagiario"),
    SeniorityLevel.JUNIOR: ("junior", "júnior", "jr"),
    SeniorityLevel.MID: ("mid", "mid-level", "middle", "pleno"),
    SeniorityLevel.SENIOR: ("senior", "sênior", "sr"),
    SeniorityLevel.STAFF: ("staff",),
    SeniorityLevel.PRINCIPAL: ("principal",),
}


def normalize_seniority(value):
    if value is None or isinstance(value, SeniorityLevel):
        return value
    normalized = str(value).strip().lower()
    return next((level for level, aliases in SENIORITY_ALIASES.items() if normalized in aliases), None)


def detect_seniority(text):
    """Return the highest explicit ordinal level found in text."""
    lowered = (text or "").lower()
    detected = []
    for level, aliases in SENIORITY_ALIASES.items():
        if any(re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", lowered) for alias in aliases):
            detected.append(level)
    return max(detected) if detected else None


class SeniorityPolicy:
    CONFIDENT_GATE = 0.8

    def evaluate(self, candidate: CandidateSeniority | None, opportunity: OpportunitySeniority | None):
        if candidate is None or opportunity is None:
            return SeniorityCompatibility(
                eligible=True,
                alignment=0.0,
                status="unknown",
                candidate_level=candidate.level if candidate else None,
                opportunity_level=opportunity.level if opportunity else None,
                reason="Seniority information is incomplete",
            )

        gap = int(opportunity.level) - int(candidate.level)
        confident = candidate.confidence >= self.CONFIDENT_GATE and opportunity.confidence >= self.CONFIDENT_GATE
        if gap <= 0:
            return SeniorityCompatibility(True, 1.0, "compatible", candidate.level, opportunity.level, gap)
        if not confident:
            return SeniorityCompatibility(
                True, 0.0, "uncertain", candidate.level, opportunity.level, gap,
                "Seniority mismatch is not confident enough for exclusion",
            )
        if gap == 1 and candidate.allow_stretch:
            return SeniorityCompatibility(
                True, 0.5, "stretch", candidate.level, opportunity.level, gap,
                "Opportunity is one level above the candidate and stretch roles are allowed",
            )
        return SeniorityCompatibility(
            False, 0.0, "ineligible", candidate.level, opportunity.level, gap,
            "Opportunity seniority exceeds the candidate preference",
        )
