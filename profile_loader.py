"""Load structured career profile data and expose the legacy matcher shape."""

import json
from copy import deepcopy
from pathlib import Path


REQUIRED_COMPETENCY_FIELDS = {"id", "label", "status", "evidence", "confidence", "target_relevance"}
REQUIRED_SKILL_FIELDS = {"id", "label", "category", "aliases", "related_skills"}
REQUIRED_ROLE_FIELDS = {"id", "label", "priority", "titles", "strong_signals", "optional_signals"}
VALID_STATUSES = {"strong", "working", "developing", "learning"}


def _read_json(path):
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _validate_items(items, required_fields, label):
    if not isinstance(items, list) or not items:
        raise ValueError(f"{label} must be a non-empty list")
    for item in items:
        if not isinstance(item, dict) or not required_fields.issubset(item):
            missing = required_fields - set(item) if isinstance(item, dict) else required_fields
            raise ValueError(f"Invalid {label} item; missing fields: {sorted(missing)}")


def normalize_weights(competencies, allowed_skill_ids):
    """Normalize target relevance for skills present in the matcher vocabulary."""
    raw = {
        item["id"]: float(item["target_relevance"])
        for item in competencies
        if item["id"] in allowed_skill_ids and float(item["target_relevance"]) > 0
    }
    total = sum(raw.values())
    if not total:
        raise ValueError("No positive target_relevance values for supported skills")
    return {skill_id: value / total for skill_id, value in raw.items()}


def load_profile_config(profile_dir=None, fallback=None):
    """Return structured data plus MEU_PERFIL/SKILL_WEIGHTS/SKILL_VARIATIONS.

    Any read or validation error returns a deep copy of ``fallback`` when given.
    """
    base_dir = Path(profile_dir) if profile_dir else Path(__file__).resolve().parent / "profile"
    try:
        professional = _read_json(base_dir / "professional_profile.json")
        ontology = _read_json(base_dir / "skills_ontology.json")
        roles = _read_json(base_dir / "role_families.json")

        competencies = professional.get("competencies")
        skills = ontology.get("skills")
        role_families = roles.get("role_families")
        _validate_items(competencies, REQUIRED_COMPETENCY_FIELDS, "competencies")
        _validate_items(skills, REQUIRED_SKILL_FIELDS, "skills")
        _validate_items(role_families, REQUIRED_ROLE_FIELDS, "role_families")

        if any(item["status"] not in VALID_STATUSES for item in competencies):
            raise ValueError("Unknown competency status")

        variations = {item["id"]: list(dict.fromkeys(item["aliases"])) for item in skills}
        weights = normalize_weights(competencies, set(variations))
        positioning = professional.get("positioning", {})
        keywords = [
            title.lower()
            for family in role_families
            if family["priority"] >= 0.7
            for title in family["titles"]
        ]
        legacy_profile = {
            "skills": list(weights),
            "keywords_vagas": list(dict.fromkeys(keywords)),
            "nivel_experiencia": professional.get("experience_years", 4),
            "localizacao": professional.get("location", "remoto"),
            "tipo_vaga": professional.get("employment_types", ["clt", "pj"]),
        }
        return {
            "MEU_PERFIL": legacy_profile,
            "SKILL_WEIGHTS": weights,
            "SKILL_VARIATIONS": variations,
            "PROFESSIONAL_PROFILE": professional,
            "SKILLS_ONTOLOGY": ontology,
            "ROLE_FAMILIES": roles,
            "POSITIONING": positioning,
            "loaded_from_files": True,
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        if fallback is None:
            raise
        result = deepcopy(fallback)
        result["loaded_from_files"] = False
        return result
