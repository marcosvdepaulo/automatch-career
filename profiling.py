"""Build independent candidate profiles from explicitly supplied sources."""
import re
from dataclasses import replace
from uuid import uuid4
from domain.models import CandidateCompetency, CandidateProfile, CandidateSeniority, CareerInterest, Evidence
from seniority import detect_seniority, normalize_seniority

class CandidateProfileBuilder:
    def from_cv_text(self, text, ontology, candidate_id=None, version="cv-v1"):
        if not text or not text.strip():
            raise ValueError("currículo sem texto extraível")
        competencies = []
        for skill_id, aliases in ontology.skill_variations.items():
            evidence = _skill_evidence(text, skill_id, aliases)
            if evidence:
                years = [item.metadata.get("experience_years") for item in evidence]
                explicit_years = [value for value in years if value is not None]
                competencies.append(CandidateCompetency(
                    skill_id=skill_id,
                    evidence=evidence,
                    experience_years=max(explicit_years) if explicit_years else None,
                    context=evidence[0].description,
                ))
        if not competencies:
            raise ValueError("nenhuma skill conhecida foi encontrada no currículo")
        profile_years = [item.experience_years for item in competencies if item.experience_years is not None]
        detected_level = detect_seniority(text)
        seniorities = ()
        if detected_level is not None:
            seniorities = (CandidateSeniority(
                detected_level,
                0.6,
                (Evidence("cv", "Explicit seniority marker in CV", metadata={"seniority": detected_level.slug}),),
            ),)
        return CandidateProfile(
            candidate_id=candidate_id or f"request-{uuid4()}",
            competencies=tuple(competencies),
            seniorities=seniorities,
            experience_years=max(profile_years) if profile_years else None,
            version=version,
        )

    def from_mapping(self, data):
        competencies = tuple(CandidateCompetency(
            skill_id=item["skill_id"], proficiency=item.get("proficiency"), confidence=item.get("confidence"),
            experience_years=item.get("experience_years"), context=item.get("context"), depth=item.get("depth"),
            evidence=tuple(Evidence(**e) for e in item.get("evidence", []))) for item in data.get("competencies", []))
        interests = tuple(CareerInterest(item["role_family_id"], float(item["priority"]),
            tuple(Evidence(**e) for e in item.get("evidence", []))) for item in data.get("interests", []))
        seniorities = tuple(CandidateSeniority(
            level=normalize_seniority(item["level"]), confidence=float(item.get("confidence", 1.0)),
            evidence=tuple(Evidence(**e) for e in item.get("evidence", [])),
            role_family_id=item.get("role_family_id"), allow_stretch=bool(item.get("allow_stretch", False)),
        ) for item in data.get("seniorities", []))
        profile = CandidateProfile(
            candidate_id=data.get("candidate_id", ""), competencies=competencies, interests=interests,
            seniorities=seniorities, location=data.get("location"),
            employment_types=tuple(data.get("employment_types", [])),
            experience_years=data.get("experience_years"), version=data.get("version", "candidate-v1"),
        )
        profile.validate_for_matching()
        return profile

    def with_declared_seniority(self, profile, level, allow_stretch=False, role_family_id=None):
        normalized = normalize_seniority(level)
        if normalized is None:
            raise ValueError(f"senioridade desconhecida: {level}")
        declaration = CandidateSeniority(
            level=normalized,
            confidence=1.0,
            evidence=(Evidence("form", "Seniority declared by candidate", metadata={"seniority": normalized.slug}),),
            role_family_id=role_family_id,
            allow_stretch=bool(allow_stretch),
        )
        retained = tuple(item for item in profile.seniorities if item.role_family_id != role_family_id)
        return replace(profile, seniorities=retained + (declaration,))

def _contains(text, phrase):
    phrase = phrase.strip().lower()
    return bool(phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def _skill_evidence(text, skill_id, aliases):
    """Preserve explicit CV statements without inferring proficiency or depth."""
    evidence = []
    seen_contexts = set()
    lowered = text.lower()
    for alias in aliases:
        phrase = alias.strip().lower()
        if not phrase:
            continue
        for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", lowered):
            context = _context_window(text, match.start(), match.end())
            normalized = context.lower()
            if normalized in seen_contexts:
                continue
            seen_contexts.add(normalized)
            years = _explicit_experience_years(context)
            evidence.append(Evidence(
                source="cv",
                description=context,
                metadata={
                    "assertion": _assertion_type(context),
                    "experience_years": years,
                    "matched_alias": phrase,
                    "skill_id": skill_id,
                },
            ))
    return tuple(evidence)


def _context_window(text, start, end):
    """Keep evidence inside its CV line/sentence to avoid cross-section leakage."""
    line_start = max(text.rfind("\n", 0, start), text.rfind("\r", 0, start), text.rfind("•", 0, start)) + 1
    line_ends = [position for marker in ("\n", "\r", "•") if (position := text.find(marker, end)) >= 0]
    line_end = min(line_ends) if line_ends else len(text)

    sentence_start = max(line_start, max(text.rfind(marker, line_start, start) for marker in (".", "?", "!")) + 1)
    sentence_ends = [position for marker in (".", "?", "!") if (position := text.find(marker, end, line_end)) >= 0]
    sentence_end = min(sentence_ends) + 1 if sentence_ends else line_end

    return re.sub(r"\s+", " ", text[sentence_start:sentence_end]).strip()


def _explicit_experience_years(context):
    match = re.search(r"(\d+(?:[.,]\d+)?)\+?\s*(?:anos?|years?)", context.lower())
    return float(match.group(1).replace(",", ".")) if match else None


def _assertion_type(context):
    lowered = context.lower()
    negative = (
        "sem experiência", "sem experiencia", "no experience", "nunca trabalhei",
        "apenas nas vagas que recruto", "only in jobs i recruit",
    )
    if any(marker in lowered for marker in negative):
        return "negative"
    practical = (
        "experiência prática", "experiencia pratica", "em produção", "em producao",
        "in production", "desenvolvi", "implementei", "construí", "construi",
        "maintained", "implemented", "built",
    )
    if _explicit_experience_years(context) is not None or any(marker in lowered for marker in practical):
        return "practical"
    learning = ("aprendendo", "estudando", "learning", "curso", "coursework")
    if any(marker in lowered for marker in learning):
        return "learning"
    return "mention"
