import unittest
from unittest.mock import Mock, patch

from api.match import processar_requisicao
from domain.models import CandidateCompetency, CandidateProfile, CandidateSeniority, Evidence, SeniorityLevel
from matcher import CareerMatcher
from ontology import load_ontology
from opportunity_parser import OpportunityProfileParser
from storage.repository import NullRepository


def skilled_junior(allow_stretch=False):
    return CandidateProfile(
        candidate_id="junior-candidate",
        competencies=(
            CandidateCompetency("python", (Evidence("project", "Python API"),), "strong", .9, depth="deployed"),
            CandidateCompetency("apis", (Evidence("project", "REST API"),), "strong", .9, depth="deployed"),
        ),
        seniorities=(CandidateSeniority(
            SeniorityLevel.JUNIOR,
            1.0,
            (Evidence("form", "Declared junior"),),
            allow_stretch=allow_stretch,
        ),),
    )


class SeniorityTests(unittest.TestCase):
    def setUp(self):
        self.ontology = load_ontology()
        self.parser = OpportunityProfileParser(self.ontology)
        self.matcher = CareerMatcher(self.ontology)

    def test_parser_normalizes_portuguese_and_english_levels(self):
        junior = self.parser.parse("Desenvolvedor Python Júnior", "Python e APIs", "junior")
        mid = self.parser.parse("Pleno Applied AI Engineer", "Python e APIs", "mid")
        senior = self.parser.parse("Senior Applied AI Engineer", "Python e APIs", "senior")

        self.assertEqual(junior.seniority.level, SeniorityLevel.JUNIOR)
        self.assertEqual(mid.seniority.level, SeniorityLevel.MID)
        self.assertEqual(senior.seniority.level, SeniorityLevel.SENIOR)

    def test_same_technical_fit_does_not_make_junior_eligible_for_senior_role(self):
        candidate = skilled_junior()
        junior_role = self.parser.parse("Junior Applied AI Engineer", "Requirements: Python and APIs", "junior")
        senior_role = self.parser.parse("Senior Applied AI Engineer", "Requirements: Python and APIs", "senior")

        junior_fit = self.matcher.assess(candidate, junior_role)
        senior_fit = self.matcher.assess(candidate, senior_role)

        self.assertEqual(junior_fit.dimension_scores["technical_fit"], senior_fit.dimension_scores["technical_fit"])
        self.assertTrue(junior_fit.eligible)
        self.assertFalse(senior_fit.eligible)
        self.assertEqual(senior_fit.seniority.status, "ineligible")

    def test_one_level_stretch_is_explicitly_opt_in(self):
        mid_role = self.parser.parse("Mid Applied AI Engineer", "Requirements: Python and APIs", "mid")
        self.assertFalse(self.matcher.assess(skilled_junior(False), mid_role).eligible)
        stretch = self.matcher.assess(skilled_junior(True), mid_role)
        self.assertTrue(stretch.eligible)
        self.assertEqual(stretch.seniority.status, "stretch")

    def test_unknown_job_seniority_does_not_silently_exclude(self):
        role = self.parser.parse("Applied AI Engineer", "Requirements: Python and APIs", "unknown")
        result = self.matcher.assess(skilled_junior(), role)
        self.assertTrue(result.eligible)
        self.assertEqual(result.seniority.status, "unknown")

    def test_api_removes_ineligible_senior_job_from_results(self):
        scraper = Mock()
        scraper.buscar_todas_vagas.return_value = [
            {"external_id": "junior", "title": "Junior Applied AI Engineer", "description": "Requirements: Python and APIs", "company": "A", "platform": "fixture", "url": "https://example.test/junior"},
            {"external_id": "senior", "title": "Senior Applied AI Engineer", "description": "Requirements: Python and APIs", "company": "B", "platform": "fixture", "url": "https://example.test/senior"},
        ]
        candidate = CandidateProfile(
            candidate_id="api-junior",
            competencies=skilled_junior().competencies,
        )
        with patch("api.match.cv_parser.construir_perfil_do_cv", return_value=candidate), \
             patch("api.match.VagasScraper", return_value=scraper), \
             patch("api.match.create_repository", return_value=NullRepository()):
            response = processar_requisicao(b"pdf", "api-junior", "junior", False)

        self.assertEqual(response["total_excluido_por_senioridade"], 1)
        self.assertEqual([job["external_id"] for job in response["top_vagas"]], ["junior"])


if __name__ == "__main__":
    unittest.main()
