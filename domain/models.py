"""Infrastructure-free domain objects for career fit assessment."""

from dataclasses import dataclass, field
from typing import Any


class IncompleteCandidateProfile(ValueError):
    """Raised when matching is requested without usable candidate evidence."""


@dataclass(frozen=True)
class Evidence:
    source: str
    description: str
    reference: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateCompetency:
    skill_id: str
    evidence: tuple[Evidence, ...]
    proficiency: str | None = None
    confidence: float | None = None
    experience_years: float | None = None
    context: str | None = None
    depth: str | None = None


@dataclass(frozen=True)
class CareerInterest:
    role_family_id: str
    priority: float
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class CandidateProfile:
    candidate_id: str
    competencies: tuple[CandidateCompetency, ...]
    interests: tuple[CareerInterest, ...] = ()
    location: str | None = None
    employment_types: tuple[str, ...] = ()
    experience_years: float | None = None
    version: str = "candidate-v1"

    def validate_for_matching(self) -> None:
        if not self.candidate_id.strip():
            raise IncompleteCandidateProfile("candidate_id is required")
        if not self.competencies:
            raise IncompleteCandidateProfile("candidate profile has no competency evidence")
        if any(not competency.evidence for competency in self.competencies):
            raise IncompleteCandidateProfile("every competency must have provenance evidence")

    @property
    def competency_map(self) -> dict[str, CandidateCompetency]:
        return {item.skill_id: item for item in self.competencies}

    @property
    def interest_map(self) -> dict[str, float]:
        return {item.role_family_id: item.priority for item in self.interests}

    @property
    def search_terms(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.skill_id.replace("_", " ") for item in self.competencies))


@dataclass(frozen=True)
class OpportunityProfile:
    opportunity_id: str
    title: str
    raw_description: str
    role_family_id: str | None = None
    required_skills: tuple[str, ...] = ()
    desired_skills: tuple[str, ...] = ()
    mentioned_skills: tuple[str, ...] = ()
    seniority: str | None = None
    responsibilities: tuple[str, ...] = ()
    context: str | None = None
    domain: str | None = None
    location: str | None = None
    employment_type: str | None = None


@dataclass(frozen=True)
class FitAssessment:
    candidate_id: str
    opportunity_id: str
    overall_score: float
    dimension_scores: dict[str, float]
    strengths: tuple[str, ...] = ()
    partial_matches: tuple[str, ...] = ()
    hard_gaps: tuple[str, ...] = ()
    trainable_gaps: tuple[str, ...] = ()
    transferable_skills: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    improvement_suggestions: tuple[str, ...] = ()
    role_family_id: str | None = None
    matcher_version: str = "4.0-domain"

    @property
    def level(self) -> str:
        if self.overall_score >= 70:
            return "Alta"
        if self.overall_score >= 40:
            return "Média"
        return "Baixa"

    def to_dict(self) -> dict[str, Any]:
        result = {
            "score": self.overall_score, "level": self.level,
            "matcher_version": self.matcher_version,
            "role_family": self.role_family_id or "unknown",
            "strengths": list(self.strengths), "strong_matches": list(self.strengths),
            "matches": list(self.strengths + self.partial_matches),
            "partial_matches": list(self.partial_matches), "hard_gaps": list(self.hard_gaps),
            "trainable_gaps": list(self.trainable_gaps),
            "transferable_skills": list(self.transferable_skills),
            "reasons": list(self.reasons),
            "improvement_suggestions": list(self.improvement_suggestions),
        }
        result.update(self.dimension_scores)
        result["matched_evidence_strength"] = self.dimension_scores.get("evidence_strength", 0)
        result["hard_gap_penalty"] = self.dimension_scores.get("hard_gap_penalty", 0)
        return result
