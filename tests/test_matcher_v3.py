import unittest
from copy import deepcopy
from unittest.mock import patch

from config import Config
from matcher import CareerMatcher
from scrapers import VagasScraper
import cv_parser


SCENARIOS = {
    "applied_ai": ("Applied AI Engineer", "Python, APIs, LLM and RAG."),
    "devops": ("Senior DevOps Engineer", "Python, AWS, Git, CI/CD, Kubernetes and Terraform."),
    "classic_ml": ("Machine Learning Engineer", "Requirements: Python, PyTorch, model training, CUDA and MLOps."),
    "interactive_ai": ("AI Gameplay Engineer", "LLMs, agents, game systems and interactive experiences."),
    "python": ("Python Developer", "Build services with Python and APIs."),
}


class MatcherV3Tests(unittest.TestCase):
    def setUp(self):
        self.matcher = CareerMatcher(Config())

    def match(self, key):
        title, description = SCENARIOS[key]
        return self.matcher.calculate_match(description, title)

    def test_applied_ai_is_primary_and_high_fit(self):
        result = self.match("applied_ai")
        self.assertEqual(result["role_family"], "applied_ai")
        self.assertEqual(result["role_priority"], "primary")
        self.assertGreaterEqual(result["score"], 70)
        self.assertLessEqual(len(result["hard_gaps"]), 1)

    def test_devops_is_low_priority_despite_shared_skills(self):
        result = self.match("devops")
        self.assertEqual(result["role_family"], "devops")
        self.assertEqual(result["role_priority"], "low_priority")
        self.assertLess(result["score"], 70)

    def test_classic_ml_required_gaps_reduce_score(self):
        result = self.match("classic_ml")
        self.assertEqual(result["role_family"], "classic_ml")
        self.assertTrue({"pytorch", "model_training", "cuda", "mlops"}.issubset(result["hard_gaps"]))
        self.assertLess(result["score"], 50)

    def test_interactive_ai_is_competitive_without_false_strength(self):
        result = self.match("interactive_ai")
        self.assertEqual(result["role_family"], "ai_games_creative_technology")
        self.assertEqual(result["role_priority"], "special_interest")
        self.assertIn("ai_agents", result["partial_matches"])
        self.assertNotIn("game_systems", result["strong_matches"])
        self.assertGreater(result["score"], 40)

    def test_generic_python_does_not_outrank_applied_ai(self):
        generic = self.match("python")
        applied = self.match("applied_ai")
        self.assertLess(generic["role_fit"], applied["role_fit"])
        self.assertLess(generic["score"], applied["score"])

    def test_legacy_contract_remains_available(self):
        result = self.match("applied_ai")
        self.assertTrue({"score", "matches", "level"}.issubset(result))
        self.assertEqual(result["matcher_version"], "3.1-heuristic")

    def test_company_name_does_not_make_generic_role_applied_ai(self):
        company, title = VagasScraper._separar_titulo_wwr("Stellar AI: Senior Software Engineer")
        result = self.matcher.calculate_match("Build reliable distributed software.", title)
        self.assertEqual((company, title), ("Stellar AI", "Senior Software Engineer"))
        self.assertNotEqual(result["role_family"], "applied_ai")

    def test_wwr_company_name_does_not_create_git_skill_match(self):
        _, title = VagasScraper._separar_titulo_wwr("GitLab: AI Engineer")
        description = VagasScraper._remover_mencoes_da_empresa(
            "Headquarters: Remote. GitLab builds an orchestration platform.", "GitLab"
        )
        result = self.matcher.calculate_match(description, title)
        self.assertNotIn("git", result["strong_matches"])

    def test_flattened_requirements_create_ml_hard_gaps(self):
        description = (
            "About the team. Requirements include hands-on experience with PyTorch, "
            "TensorFlow, training machine learning models, NVIDIA CUDA, model serving, "
            "deep learning and statistics."
        )
        result = self.matcher.calculate_match(description, "Machine Learning Engineer")
        expected = {"pytorch", "tensorflow", "model_training", "cuda", "mlops", "deep_learning"}
        self.assertTrue(expected.issubset(result["hard_gaps"]))
        self.assertNotIn("statistics", result["hard_gaps"])
        self.assertLess(result["skill_fit"], 0.3)

    def test_skill_fit_uses_all_detected_job_skills_as_denominator(self):
        description = "Requirements: Python, PyTorch, NVIDIA CUDA and MLOps."
        partial = self.matcher.calculate_match(description, "Machine Learning Engineer")

        covered_config = Config()
        profile = deepcopy(covered_config.PROFESSIONAL_PROFILE)
        for skill_id in ("pytorch", "cuda", "mlops"):
            profile["competencies"].append({
                "id": skill_id, "label": skill_id, "status": "strong",
                "evidence": ["Test fixture evidence"], "evidence_maturity": "working_product",
                "confidence": 0.9, "target_relevance": 0.8,
            })
        covered_config.PROFESSIONAL_PROFILE = profile
        covered = CareerMatcher(covered_config).calculate_match(description, "Machine Learning Engineer")

        self.assertLess(partial["skill_fit"], covered["skill_fit"])
        self.assertLess(partial["skill_fit"], 0.4)

    def test_matched_evidence_strength_is_explicit_compatibility_alias(self):
        result = self.match("applied_ai")
        self.assertEqual(result["matched_evidence_strength"], result["evidence_strength"])

    def test_cv_preserves_known_relevance_and_marks_lexical_evidence(self):
        config = Config()
        with patch.object(cv_parser, "extrair_texto_pdf", return_value="Python Git Kubernetes"):
            _, weights = cv_parser.gerar_perfil_do_cv("ignored.pdf", config)
        self.assertGreater(weights["python"], weights["git"])
        self.assertIn("kubernetes", config.CV_SKILL_EVIDENCE)


if __name__ == "__main__":
    unittest.main()
