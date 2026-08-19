"""Domain matcher: candidate + opportunity -> fit assessment."""
from domain.models import FitAssessment, IncompleteCandidateProfile

MATCHER_VERSION = "4.1-domain-traceable"
PROFICIENCY = {"learning": .35, "developing": .6, "working": .85, "strong": 1.0}
DEPTH = {"unspecified": .5, "research": .35, "prototype": .65,
         "functional_prototype": .85, "working_product": .95, "deployed": 1.0}
ASSERTION_STRENGTH = {"negative": 0.0, "mention": .15, "learning": .35, "practical": 1.0}
EVIDENCE_STRENGTH = {"negative": 0.0, "mention": .25, "learning": .5, "practical": 1.0}

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
                technical_strength = self._technical_strength(competency)
                evidence_strength = self._evidence_strength(competency)
                scored.append((technical_strength, evidence_strength, kind))
                if technical_strength >= .72:
                    strengths.append(skill_id)
                elif technical_strength > 0:
                    partial.append(skill_id)
                elif kind == "required":
                    hard.append(skill_id)
            elif kind == "required":
                adjacent = self._adjacent_competencies(skill_id, competencies)
                if adjacent:
                    trainable.append(skill_id)
                    transferable.extend(adjacent)
                else:
                    hard.append(skill_id)
        role_fit = self._role_fit(candidate, opportunity.role_family_id)
        interest_known = opportunity.role_family_id in candidate.interest_map
        interest = candidate.interest_map.get(opportunity.role_family_id, 0.0) if opportunity.role_family_id else 0.0
        technical_fit = self._technical_fit(scored, requirements)
        evidence = self._evidence_fit(scored, requirements)
        transferability = min(1.0, len(set(transferable)) / max(1, len(opportunity.required_skills)))
        hard_penalty = min(.4, len(hard) * .11)
        contributions = {
            "role_fit_contribution": role_fit * .3,
            "technical_fit_contribution": technical_fit * .3,
            "evidence_strength_contribution": evidence * .2,
            "interest_alignment_contribution": interest * .1,
            "skill_transferability_contribution": transferability * .1,
        }
        base = sum(contributions.values())
        score = round(max(0, min(1, base - hard_penalty)) * 100, 1)
        reasons = self._reasons(opportunity, strengths, partial, hard, trainable, interest_known)
        suggestions = tuple(f"Desenvolver evidência prática em {skill}" for skill in hard + trainable)
        dimensions = {"role_fit": round(role_fit, 3), "technical_fit": round(technical_fit, 3),
                      "skill_fit": round(technical_fit, 3),
                      "evidence_strength": round(evidence, 3), "interest_alignment": round(interest, 3),
                      "skill_transferability": round(transferability, 3), "hard_gap_penalty": round(hard_penalty, 3),
                      "base_score": round(base, 3),
                      **{name: round(value, 3) for name, value in contributions.items()}}
        return FitAssessment(candidate.candidate_id, opportunity.opportunity_id, score, dimensions,
            tuple(strengths), tuple(partial), tuple(hard), tuple(trainable), tuple(dict.fromkeys(transferable)),
            reasons, suggestions, opportunity.role_family_id, MATCHER_VERSION)

    def _adjacent_competencies(self, missing, competencies):
        related = set(self.ontology.skills.get(missing, {}).get("related_skills", []))
        adjacent = []
        for skill_id, competency in competencies.items():
            reverse = missing in self.ontology.skills.get(skill_id, {}).get("related_skills", [])
            if (skill_id in related or reverse) and self._technical_strength(competency) >= .65:
                adjacent.append(skill_id)
        return adjacent

    @staticmethod
    def _technical_strength(competency):
        """Use explicit competency facts only; unknown values add no invented signal."""
        signals = []
        if competency.proficiency in PROFICIENCY:
            signals.append(PROFICIENCY[competency.proficiency])
        if competency.depth in DEPTH:
            signals.append(DEPTH[competency.depth])
        if competency.experience_years is not None:
            signals.append(1.0 if competency.experience_years > 0 else 0.0)
        assertions = [item.metadata.get("assertion") for item in competency.evidence]
        signals.extend(ASSERTION_STRENGTH[item] for item in assertions if item in ASSERTION_STRENGTH)
        if not assertions and any(item.source in {"project", "github"} for item in competency.evidence):
            signals.append(1.0)
        return sum(signals) / len(signals) if signals else 0.0

    @staticmethod
    def _evidence_strength(competency):
        signals = []
        for evidence in competency.evidence:
            assertion = evidence.metadata.get("assertion")
            if assertion in EVIDENCE_STRENGTH:
                signals.append(EVIDENCE_STRENGTH[assertion])
            elif evidence.source in {"project", "github"}:
                signals.append(1.0)
            elif evidence.source == "cv":
                signals.append(.25)
            if evidence.confidence is not None:
                signals.append(max(0, min(1, evidence.confidence)))
        if competency.confidence is not None:
            signals.append(max(0, min(1, competency.confidence)))
        return sum(signals) / len(signals) if signals else 0.0

    def _role_fit(self, candidate, role_family_id):
        if not role_family_id:
            return 0.0
        family = next((item for item in self.ontology.role_families if item["id"] == role_family_id), None)
        if not family:
            return 0.0
        strong_signals = family.get("strong_signals", [])
        if not strong_signals:
            return 0.0
        competencies = candidate.competency_map
        return sum(self._technical_strength(competencies[skill]) for skill in strong_signals if skill in competencies) / len(strong_signals)

    @staticmethod
    def _technical_fit(scored, requirements):
        if not requirements: return 0.0
        weights = {"required": 1.0, "mentioned": .75, "desired": .5}
        return min(1, sum(technical * weights[kind] for technical, _, kind in scored) / sum(weights[kind] for _, kind in requirements))

    @staticmethod
    def _evidence_fit(scored, requirements):
        if not requirements: return 0.0
        weights = {"required": 1.0, "mentioned": .75, "desired": .5}
        return min(1, sum(evidence * weights[kind] for _, evidence, kind in scored) / sum(weights[kind] for _, kind in requirements))

    @staticmethod
    def _reasons(opportunity, strengths, partial, hard, trainable, interest_known):
        reasons = [f"Role family: {opportunity.role_family_id}" if opportunity.role_family_id else "Role family não identificada"]
        if strengths: reasons.append(f"Evidência forte: {', '.join(strengths[:3])}")
        if partial: reasons.append(f"Evidência parcial: {', '.join(partial[:3])}")
        if trainable: reasons.append(f"Gaps treináveis por adjacência: {', '.join(trainable[:3])}")
        if hard: reasons.append(f"Gaps sem base demonstrada: {', '.join(hard[:3])}")
        if not interest_known: reasons.append("Interesse do candidato não informado")
        return tuple(reasons[:5])
