"""Load global skill and role knowledge. No candidate data belongs here."""
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Ontology:
    skills: dict
    role_families: tuple[dict, ...]
    @property
    def skill_variations(self):
        return {key: tuple(dict.fromkeys([key.replace("_", " "), *item.get("aliases", [])])) for key, item in self.skills.items()}

def load_ontology(profile_dir=None):
    base = Path(profile_dir) if profile_dir else Path(__file__).resolve().parent / "profile"
    with (base / "skills_ontology.json").open(encoding="utf-8-sig") as file:
        skills = json.load(file).get("skills", [])
    with (base / "role_families.json").open(encoding="utf-8-sig") as file:
        roles = json.load(file).get("role_families", [])
    if not skills or not roles:
        raise ValueError("ontology requires skills and role families")
    if any("priority" in role for role in roles):
        raise ValueError("candidate priority cannot be stored in role ontology")
    return Ontology({item["id"]: item for item in skills}, tuple(roles))
