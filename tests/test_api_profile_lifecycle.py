import unittest
from unittest.mock import Mock, patch

from api.match import processar_requisicao
from ontology import load_ontology
from profiling import CandidateProfileBuilder
from storage.repository import NullRepository


class ApiProfileLifecycleTests(unittest.TestCase):
    def test_response_preserves_profile_and_assessment_trace(self):
        ontology = load_ontology()
        candidate = CandidateProfileBuilder().from_cv_text(
            "8 years practical experience building Python APIs in production.",
            ontology,
            candidate_id="candidate-front",
        )
        scraper = Mock()
        scraper.buscar_todas_vagas.return_value = [{
            "external_id": "job-1",
            "title": "Applied AI Engineer",
            "description": "Requirements: Python and APIs",
            "company": "Example",
            "platform": "fixture",
            "url": "https://example.test/job-1",
        }]

        with patch("api.match.cv_parser.construir_perfil_do_cv", return_value=candidate), \
             patch("api.match.VagasScraper", return_value=scraper), \
             patch("api.match.create_repository", return_value=NullRepository()):
            response = processar_requisicao(b"synthetic-pdf", candidate_id="candidate-front")

        lifecycle = response["profile_lifecycle"]
        self.assertEqual(lifecycle["candidate_id"], "candidate-front")
        self.assertEqual(lifecycle["matcher_version"], "4.1-domain-traceable")
        python = next(item for item in lifecycle["competencies"] if item["skill_id"] == "python")
        self.assertEqual(python["assertions"], ["practical"])
        self.assertEqual(python["experience_years"], 8)
        details = response["top_vagas"][0]["match_details"]
        self.assertIn("technical_fit", details)
        self.assertIn("evidence_strength", details)


if __name__ == "__main__":
    unittest.main()
