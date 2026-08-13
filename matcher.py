"""Matcher v3: deterministic, explainable career-fit scoring."""

import re

MATCHER_VERSION = "3.1-heuristic"
SCORE_WEIGHTS = {"role_fit": 0.35, "skill_fit": 0.30, "evidence_strength": 0.20, "interest_alignment": 0.15}
STATUS_MULTIPLIERS = {"strong": 1.0, "working": 0.85, "developing": 0.60, "learning": 0.35}
MATURITY_MULTIPLIERS = {"deployed": 1.0, "working_product": 0.95, "functional_prototype": 0.85, "prototype": 0.65, "architecture": 0.45, "research": 0.35, "roadmap": 0.25, "incomplete": 0.20, "unspecified": 0.50}
PRIORITY_LABELS = {1.0: "primary", 0.85: "secondary", 0.7: "special_interest", 0.3: "low_priority"}
INTEREST_ALIGNMENT = {"primary": 1.0, "secondary": 0.85, "special_interest": 0.75, "low_priority": 0.20, "unknown": 0.35}
REQUIRED_MARKERS = ("required", "must have", "requirements", "required experience", "obrigatório", "obrigatorio", "requisitos", "necessário", "necessario", "essential", "exigindo")
PREFERRED_MARKERS = ("preferred", "nice to have", "desirable", "diferencial", "desejável", "desejavel")


class CareerMatcher:
    def __init__(self, config):
        self.config = config
        self.skills_weights = config.SKILL_WEIGHTS
        ontology = getattr(config, "SKILLS_ONTOLOGY", {"skills": []})
        roles = getattr(config, "ROLE_FAMILIES", {"role_families": []})
        profile = getattr(config, "PROFESSIONAL_PROFILE", {})
        self.roles = roles.get("role_families", [])
        self.skill_definitions = {item["id"]: item for item in ontology.get("skills", [])}
        self.competencies = {item["id"]: item for item in profile.get("competencies", [])}

    def calculate_match(self, job_description, job_title):
        title, description = (job_title or "").lower(), (job_description or "").lower()
        detected = self._detect_job_skills(title, description)
        family, role_fit = self._match_role_family(title, description, detected)
        priority = self._priority_label(family.get("priority")) if family else "unknown"
        interest = INTEREST_ALIGNMENT[priority]
        strong_matches, partial_matches, missing_required, strengths = [], [], [], []
        for skill_id, requirement in detected.items():
            competency = self._competency_for(skill_id)
            if not competency or self._insufficient_required_evidence(competency, requirement):
                if requirement == "required":
                    missing_required.append(skill_id)
                if not competency:
                    continue
            if not competency:
                continue
            strength = self._competency_strength(competency)
            strengths.append((skill_id, strength, requirement))
            (strong_matches if strength >= 0.72 else partial_matches).append(skill_id)
        skill_fit = self._skill_fit(strengths, detected)
        evidence_strength = self._evidence_fit(strengths)
        hard_gaps = self._hard_gaps(missing_required, family)
        hard_gap_penalty = self._gap_penalty(hard_gaps, family)
        base_score = sum((role_fit, skill_fit, evidence_strength, interest)[i] * weight for i, weight in enumerate(SCORE_WEIGHTS.values()))
        final_score = max(0.0, min(1.0, base_score - hard_gap_penalty))
        matches = strong_matches + [item for item in partial_matches if item not in strong_matches]
        return {
            "score": round(final_score * 100, 1), "matches": matches, "level": self._classificar_nivel(final_score),
            "matcher_version": MATCHER_VERSION, "role_family": family["id"] if family else "unknown",
            "role_family_label": family["label"] if family else "Unknown", "role_priority": priority,
            "role_fit": round(role_fit, 3), "skill_fit": round(skill_fit, 3),
            "evidence_strength": round(evidence_strength, 3), "interest_alignment": round(interest, 3),
            # Explicit alias: evidence is maturity of covered skills, not job coverage.
            "matched_evidence_strength": round(evidence_strength, 3),
            "hard_gap_penalty": round(hard_gap_penalty, 3), "strong_matches": strong_matches,
            "partial_matches": partial_matches, "missing_required": missing_required, "hard_gaps": hard_gaps,
            "reasons": self._reasons(family, role_fit, strengths, hard_gaps, priority),
        }

    def _match_role_family(self, title, description, detected):
        best_family, best_score = None, 0.0
        for family in self.roles:
            title_score = max((self._phrase_similarity(title, candidate.lower()) for candidate in family["titles"]), default=0.0)
            strong_ratio = sum(self._signal_present(s, description, detected) for s in family["strong_signals"]) / max(1, len(family["strong_signals"]))
            optional_ratio = sum(self._signal_present(s, description, detected) for s in family["optional_signals"]) / max(1, len(family["optional_signals"]))
            score = min(1.0, title_score * 0.72 + strong_ratio * 0.20 + optional_ratio * 0.08)
            if score > best_score:
                best_family, best_score = family, score
        return (None, 0.15) if best_score < 0.28 else (best_family, best_score)

    @staticmethod
    def _phrase_similarity(title, candidate):
        title_tokens = set(re.findall(r"[a-z0-9]+", title)) - {"senior", "sr", "junior", "jr", "lead"}
        candidate_tokens = set(re.findall(r"[a-z0-9]+", candidate))
        if not title_tokens or not candidate_tokens:
            return 0.0
        overlap = len(title_tokens & candidate_tokens) / len(candidate_tokens)
        # All words scattered through a title are weaker than the actual title
        # phrase ("AI Gameplay Engineer" must not equal generic "AI Engineer").
        token_score = overlap * 0.82 if overlap >= 0.60 else overlap * 0.35
        return max(1.0 if candidate in title else 0.0, token_score)

    def _signal_present(self, signal, text, detected):
        return signal in detected or self._contains(text, signal.replace("_", " "))

    def _detect_job_skills(self, title, description):
        detected = {}
        for skill_id, variations in self.config.SKILL_VARIATIONS.items():
            aliases = list(variations) + [skill_id.replace("_", " ")]
            if any(self._contains(title, alias) for alias in aliases):
                detected[skill_id] = "required"
                continue
            occurrences = [
                match.start()
                for alias in aliases if alias.strip()
                for match in re.finditer(
                    r"(?<!\w)" + re.escape(alias.strip().lower()) + r"(?!\w)", description
                )
            ]
            if not occurrences:
                continue
            requirements = [self._requirement_near(description, position) for position in occurrences]
            if "required" in requirements:
                detected[skill_id] = "required"
            elif "preferred" in requirements:
                detected[skill_id] = "preferred"
            else:
                detected[skill_id] = "neutral"
        return detected

    @staticmethod
    def _requirement_near(description, position):
        """Use the nearest heading in a bounded window around flattened lists."""
        context = description[max(0, position - 240):position]
        required_at = max((context.rfind(marker) for marker in REQUIRED_MARKERS), default=-1)
        preferred_at = max((context.rfind(marker) for marker in PREFERRED_MARKERS), default=-1)
        if required_at > preferred_at and required_at >= 0:
            return "required"
        if preferred_at > required_at:
            return "preferred"
        return "neutral"

    @staticmethod
    def _contains(text, phrase):
        phrase = phrase.strip().lower()
        return bool(phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))

    def _competency_for(self, skill_id):
        competency = self.competencies.get(skill_id)
        cv_data = getattr(self.config, "CV_SKILL_EVIDENCE", None)
        if cv_data is None:
            return competency
        if skill_id not in cv_data:
            return None
        return competency or {"id": skill_id, "status": "learning", "confidence": 0.45, "target_relevance": 0.35, "evidence": ["Lexical presence in CV"], "evidence_maturity": "unspecified"}

    @staticmethod
    def _competency_strength(competency):
        status = STATUS_MULTIPLIERS.get(competency.get("status"), 0.0)
        confidence = max(0.0, min(1.0, float(competency.get("confidence", 0))))
        relevance = max(0.0, min(1.0, float(competency.get("target_relevance", 0))))
        maturity = MATURITY_MULTIPLIERS.get(competency.get("evidence_maturity", "unspecified"), 0.5)
        evidence_factor = 1.0 if competency.get("evidence") else 0.75
        return status * (0.45 + confidence * 0.25 + maturity * 0.20 + relevance * 0.10) * evidence_factor

    def _insufficient_required_evidence(self, competency, requirement):
        return (
            requirement == "required"
            and competency.get("status") == "learning"
            and self._competency_strength(competency) < 0.35
        )

    @staticmethod
    def _skill_fit(strengths, detected):
        if not detected:
            return 0.10
        weights = {"required": 1.0, "neutral": 0.75, "preferred": 0.50}
        achieved = sum(strength * weights[requirement] for _, strength, requirement in strengths)
        possible = sum(weights[value] for value in detected.values())
        return max(0.0, min(1.0, achieved / possible))

    @staticmethod
    def _evidence_fit(strengths):
        if not strengths:
            return 0.05
        weights = {"required": 1.0, "neutral": 0.75, "preferred": 0.50}
        return sum(strength * weights[req] for _, strength, req in strengths) / sum(weights[req] for _, _, req in strengths)

    def _hard_gaps(self, missing_required, family):
        if not family:
            return []
        signals = set(family["strong_signals"] + family["optional_signals"])
        return sorted(
            (skill for skill in missing_required if self._family_relevant(skill, signals)),
            key=lambda item: item not in set(family["strong_signals"]),
        )

    def _family_relevant(self, skill_id, family_signals):
        if skill_id in family_signals:
            return True
        related = set(self.skill_definitions.get(skill_id, {}).get("related_skills", []))
        if related & family_signals:
            return True
        return any(
            skill_id in self.skill_definitions.get(signal, {}).get("related_skills", [])
            for signal in family_signals
        )

    @staticmethod
    def _gap_penalty(hard_gaps, family):
        signals = set(family["strong_signals"]) if family else set()
        return min(0.40, sum(0.11 if gap in signals else 0.07 for gap in hard_gaps))

    @staticmethod
    def _priority_label(priority):
        return PRIORITY_LABELS.get(priority, "unknown")

    def _reasons(self, family, role_fit, strengths, hard_gaps, priority):
        reasons = [f"{'Strong' if role_fit >= 0.65 else 'Partial'} alignment with {family['label']} roles" if family else "No clear target role family identified"]
        strongest = sorted(strengths, key=lambda item: item[1], reverse=True)[:2]
        if strongest:
            labels = [self.skill_definitions.get(item[0], {}).get("label", item[0].replace("_", " ")) for item in strongest]
            reasons.append(f"Evidence supports {', '.join(labels)}")
        developing = [skill for skill, strength, _ in strengths if strength < 0.72]
        if developing:
            label = self.skill_definitions.get(developing[0], {}).get("label", developing[0].replace("_", " "))
            reasons.append(f"{label} evidence is developing rather than strong")
        if hard_gaps:
            labels = [self.skill_definitions.get(gap, {}).get("label", gap.replace("_", " ")) for gap in hard_gaps[:3]]
            reasons.append(f"Required evidence missing for {', '.join(labels)}")
        if priority == "low_priority":
            reasons.append("Role family is a lower search priority")
        return reasons[:4]

    def _skill_present(self, skill, texto):
        return any(self._contains(texto, variation) for variation in self.config.SKILL_VARIATIONS.get(skill, [skill]))

    @staticmethod
    def _classificar_nivel(score):
        if score >= 0.7:
            return "💚 Alta"
        if score >= 0.4:
            return "💛 Média"
        return "💔 Baixa"
