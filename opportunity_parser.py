"""Transform collected job text into an opportunity domain object."""
import re
from domain.models import Evidence, OpportunityProfile, OpportunitySeniority
from seniority import detect_seniority

REQUIRED = ("required", "must have", "requirements", "obrigatório", "obrigatorio", "requisitos", "essential")
PREFERRED = ("preferred", "nice to have", "desirable", "diferencial", "desejável", "desejavel")

class OpportunityProfileParser:
    def __init__(self, ontology): self.ontology = ontology
    def parse(self, title, description, opportunity_id="unknown", **metadata):
        title_text, description_text = (title or "").lower(), (description or "").lower()
        required, desired, mentioned = [], [], []
        for skill_id, aliases in self.ontology.skill_variations.items():
            positions = [m.start() for alias in aliases if alias.strip() for m in re.finditer(r"(?<!\w)" + re.escape(alias.strip().lower()) + r"(?!\w)", description_text)]
            if any(_contains(title_text, alias) for alias in aliases): required.append(skill_id)
            elif positions:
                kinds = [_near(description_text, p) for p in positions]
                (required if "required" in kinds else desired if "desired" in kinds else mentioned).append(skill_id)
        family = self._family(title_text, set(required + desired + mentioned))
        return OpportunityProfile(str(opportunity_id), title or "", description or "", family["id"] if family else None,
            tuple(required), tuple(desired), tuple(mentioned), _seniority(title_text, description_text), location=metadata.get("location"),
            employment_type=metadata.get("employment_type"), context=metadata.get("context"), domain=metadata.get("domain"))
    def _family(self, title, skills):
        best, best_score = None, 0
        for family in self.ontology.role_families:
            title_score = max((_similarity(title, candidate.lower()) for candidate in family["titles"]), default=0)
            signal_score = len(set(family["strong_signals"]) & skills) / max(1, len(family["strong_signals"]))
            score = title_score * .8 + signal_score * .2
            if score > best_score: best, best_score = family, score
        return best if best_score >= .28 else None

def _contains(text, phrase): return bool(phrase.strip() and re.search(r"(?<!\w)" + re.escape(phrase.strip().lower()) + r"(?!\w)", text))
def _near(text, position):
    context = text[max(0, position - 240):position]
    required, preferred = max((context.rfind(x) for x in REQUIRED), default=-1), max((context.rfind(x) for x in PREFERRED), default=-1)
    return "required" if required > preferred and required >= 0 else "desired" if preferred > required else "mentioned"
def _similarity(title, candidate):
    a, b = set(re.findall(r"[a-z0-9]+", title)) - {"principal","staff","senior","sr","mid","pleno","junior","jr","intern","lead"}, set(re.findall(r"[a-z0-9]+", candidate))
    if not a or not b: return 0
    overlap = len(a & b) / len(b)
    return max(1.0 if candidate in title else 0, overlap * (.82 if overlap >= .6 else .35))
def _seniority(title, description):
    title_level = detect_seniority(title)
    if title_level is not None:
        return OpportunitySeniority(
            title_level,
            1.0,
            (Evidence("job_title", title, metadata={"seniority": title_level.slug}),),
        )
    description_level = detect_seniority(description)
    if description_level is not None:
        return OpportunitySeniority(
            description_level,
            0.7,
            (Evidence("job_description", "Explicit seniority marker", metadata={"seniority": description_level.slug}),),
        )
    return None
