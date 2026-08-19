import unittest

from domain.models import CandidateProfile, IncompleteCandidateProfile, OpportunityProfile
from matcher import CareerMatcher
from ontology import load_ontology
from profiling import CandidateProfileBuilder


class DomainIsolationTests(unittest.TestCase):
    def setUp(self):
        self.ontology = load_ontology()
        self.matcher = CareerMatcher(self.ontology)
        self.opportunity = OpportunityProfile(
            opportunity_id="job-1", title="Python API Engineer", raw_description="Requirements: Python and APIs",
            role_family_id="applied_ai", required_skills=("python", "apis"),
        )

    def test_two_candidates_with_same_skill_can_score_differently(self):
        builder = CandidateProfileBuilder()
        experienced = builder.from_mapping({
            "candidate_id": "experienced", "competencies": [{"skill_id": "python", "proficiency": "strong",
            "confidence": .95, "depth": "deployed", "evidence": [{"source": "project", "description": "Production API"}]}],
            "interests": [{"role_family_id": "applied_ai", "priority": 1.0}],
        })
        lexical = builder.from_cv_text("Python", self.ontology, candidate_id="lexical")
        self.assertGreater(self.matcher.assess(experienced, self.opportunity).overall_score,
                           self.matcher.assess(lexical, self.opportunity).overall_score)

    def test_candidate_does_not_inherit_another_candidates_data(self):
        builder = CandidateProfileBuilder()
        first = builder.from_cv_text("Python and Kubernetes", self.ontology, candidate_id="first")
        second = builder.from_cv_text("JavaScript", self.ontology, candidate_id="second")
        self.assertNotIn("kubernetes", second.competency_map)
        self.assertFalse(second.interests)
        self.assertNotEqual(first.competency_map, second.competency_map)

    def test_matcher_rejects_missing_candidate(self):
        with self.assertRaises(IncompleteCandidateProfile):
            self.matcher.assess(None, self.opportunity)

    def test_matcher_rejects_candidate_without_evidence(self):
        with self.assertRaises(IncompleteCandidateProfile):
            self.matcher.assess(CandidateProfile("empty", ()), self.opportunity)


if __name__ == "__main__":
    unittest.main()
