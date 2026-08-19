"""Domain matcher: candidate + opportunity -> fit assessment."""
from domain.models import FitAssessment, IncompleteCandidateProfile

MATCHER_VERSION = "4.0-domain"
PROFICIENCY = {None: .45, "learning": .35, "developing": .6, "working": .85, "strong": 1.0}
DEPTH = {None: .5, "unspecified": .5, "research": .35, "prototype": .65,
         "functional_prototype": .85, "working_product": .95, "deployed": 1.0}

class CareerMatcher:
    def __init__(self, ontology):
        self.ontology = ontology

    def assess(self, candidate, opportunity):
        if candidate is None:
            raise IncompleteCandidateProfile("CandidateProfile is required; no default profile exists")
        candidate.validate_for_matching()
        if opportunity is None:
            raise ValueError("OpportunityProfile is required")
        competencies = candidate.competency_map
        requirements = [(skill, "required") for skill in opportunity.required_skills]
        requirements += [(skill, "desired") for skill in opportunity.desired_skills]
        requirements += [(skill, "mentioned") for skill in opportunity.mentioned_skills]
        strengths, partial, hard, trainable, transferable, scored = [], [], [], [], [], []
        for skill_id, kind in requirements:
            competency = competencies.get(skill_id)
            if competency:
                strength = self._strength(competency)
                scored.append((strength, kind))
                (strengths if strength >= .72 else partial).append(skill_id)
            elif kind == "required":
                adjacent = self._adjacent_competencies(skill_id, competencies)
                if adjacent:
                    trainable.append(skill_id)
                    transferable.extend(adjacent)
                else:
                    hard.append(skill_id)
        role_fit = 1.0 if opportunity.role_family_id else .15
        interest = candidate.interest_map.get(opportunity.role_family_id, .35) if opportunity.role_family_id else .35
        skill_fit = self._skill_fit(scored, requirements)
        evidence = sum(value for value, _ in scored) / len(scored) if scored else .05
        transferability = min(1.0, len(set(transferable)) / max(1, len(opportunity.required_skills)))
        hard_penalty = min(.4, len(hard) * .11)
        base = role_fit * .3 + skill_fit * .3 + evidence * .2 + interest * .1 + transferability * .1
        score = round(max(0, min(1, base - hard_penalty)) * 100, 1)
        reasons = self._reasons(opportunity, strengths, partial, hard, trainable, interest)
        suggestions = tuple(f"Desenvolver evidência prática em {skill}" for skill in hard + trainable)
        dimensions = {"role_fit": round(role_fit, 3), "skill_fit": round(skill_fit, 3),
                      "evidence_strength": round(evidence, 3), "interest_alignment": round(interest, 3),
                      "skill_transferability": round(transferability, 3), "hard_gap_penalty": round(hard_penalty, 3)}
        return FitAssessment(candidate.candidate_id, opportunity.opportunity_id, score, dimensions,
            tuple(strengths), tuple(partial), tuple(hard), tuple(trainable), tuple(dict.fromkeys(transferable)),
            reasons, suggestions, opportunity.role_family_id, MATCHER_VERSION)

    def _adjacent_competencies(self, missing, competencies):
        related = set(self.ontology.skills.get(missing, {}).get("related_skills", []))
        adjacent = []
        for skill_id, competency in competencies.items():
            reverse = missing in self.ontology.skills.get(skill_id, {}).get("related_skills", [])
            if (skill_id in related or reverse) and self._strength(competency) >= .65:
                adjacent.append(skill_id)
        return adjacent

    @staticmethod
    def _strength(competency):
        confidence = .5 if competency.confidence is None else max(0, min(1, competency.confidence))
        evidence_factor = min(1, .65 + .1 * len(competency.evidence))
        return PROFICIENCY.get(competency.proficiency, .45) * (.55 + confidence * .25 + DEPTH.get(competency.depth, .5) * .2) * evidence_factor

    @staticmethod
    def _skill_fit(scored, requirements):
        if not requirements: return .1
        weights = {"required": 1.0, "mentioned": .75, "desired": .5}
        return min(1, sum(value * weights[kind] for value, kind in scored) / sum(weights[kind] for _, kind in requirements))

    @staticmethod
    def _reasons(opportunity, strengths, partial, hard, trainable, interest):
        reasons = [f"Role family: {opportunity.role_family_id}" if opportunity.role_family_id else "Role family não identificada"]
        if strengths: reasons.append(f"Evidência forte: {', '.join(strengths[:3])}")
        if partial: reasons.append(f"Evidência parcial: {', '.join(partial[:3])}")
        if trainable: reasons.append(f"Gaps treináveis por adjacência: {', '.join(trainable[:3])}")
        if hard: reasons.append(f"Gaps sem base demonstrada: {', '.join(hard[:3])}")
        if interest == .35: reasons.append("Interesse do candidato não informado")
        return tuple(reasons[:5])
