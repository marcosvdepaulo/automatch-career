import unittest
from domain.models import CandidateCompetency, CandidateProfile, CareerInterest, Evidence
from matcher import CareerMatcher
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser

class MatcherDomainTests(unittest.TestCase):
    def setUp(self):
        self.ontology = load_ontology()
        self.matcher = CareerMatcher(self.ontology)
        self.parser = OpportunityProfileParser(self.ontology)
    def candidate(self):
        return CandidateProfile("a", (
            CandidateCompetency("python", (Evidence("project", "Production API"),), "strong", .95, depth="deployed"),
            CandidateCompetency("apis", (Evidence("project", "REST API"),), "working", .8, depth="working_product"),
        ), (CareerInterest("applied_ai", 1.0),))
    def test_returns_multidimensional_assessment(self):
        opportunity = self.parser.parse("Applied AI Engineer", "Requirements: Python and APIs", "job")
        result = self.matcher.assess(self.candidate(), opportunity)
        self.assertEqual(result.candidate_id, "a")
        self.assertIn("skill_fit", result.dimension_scores)
        self.assertGreater(result.overall_score, 50)
    def test_related_skill_is_trainable_not_hard_gap(self):
        candidate = CandidateProfile("a", (CandidateCompetency("python", (Evidence("project", "Automation"),), "strong", .9, depth="deployed"),))
        opportunity = self.parser.parse("API Engineer", "Requirements: APIs", "job")
        result = self.matcher.assess(candidate, opportunity)
        self.assertIn("apis", result.trainable_gaps)
        self.assertNotIn("apis", result.hard_gaps)
        self.assertIn("python", result.transferable_skills)

if __name__ == "__main__": unittest.main()
