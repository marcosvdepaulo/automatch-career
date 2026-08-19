"""Build independent candidate profiles from explicitly supplied sources."""
import re
from uuid import uuid4
from domain.models import CandidateCompetency, CandidateProfile, CareerInterest, Evidence

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
        return CandidateProfile(
            candidate_id or f"request-{uuid4()}",
            tuple(competencies),
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
        profile = CandidateProfile(data.get("candidate_id", ""), competencies, interests, data.get("location"),
            tuple(data.get("employment_types", [])), data.get("experience_years"), data.get("version", "candidate-v1"))
        profile.validate_for_matching()
        return profile

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


def _context_window(text, start, end, radius=120):
    window = text[max(0, start - radius):min(len(text), end + radius)]
    return re.sub(r"\s+", " ", window).strip()


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
