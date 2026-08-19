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
            if any(_contains(text.lower(), alias) for alias in aliases):
                competencies.append(CandidateCompetency(skill_id=skill_id, evidence=(Evidence("cv", f"Presença lexical de {skill_id} no currículo"),)))
        if not competencies:
            raise ValueError("nenhuma skill conhecida foi encontrada no currículo")
        return CandidateProfile(candidate_id or f"request-{uuid4()}", tuple(competencies), version=version)

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
