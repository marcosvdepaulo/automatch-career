import json
import tempfile
import unittest
from pathlib import Path

from config import Config
from matcher import CareerMatcher
from profile_loader import load_profile_config


class ProfileLoaderTests(unittest.TestCase):
    def test_loads_all_structured_files(self):
        loaded = load_profile_config()

        self.assertTrue(loaded["loaded_from_files"])
        self.assertIn("competencies", loaded["PROFESSIONAL_PROFILE"])
        self.assertIn("skills", loaded["SKILLS_ONTOLOGY"])
        self.assertIn("role_families", loaded["ROLE_FAMILIES"])

    def test_falls_back_when_directory_does_not_exist(self):
        fallback = {
            "MEU_PERFIL": {"skills": ["legacy"]},
            "SKILL_WEIGHTS": {"legacy": 1.0},
            "SKILL_VARIATIONS": {"legacy": ["legacy"]},
        }

        loaded = load_profile_config("missing-profile-directory", fallback=fallback)

        self.assertFalse(loaded["loaded_from_files"])
        self.assertEqual(loaded["SKILL_WEIGHTS"], {"legacy": 1.0})

    def test_falls_back_when_json_is_invalid(self):
        fallback = {"MEU_PERFIL": {}, "SKILL_WEIGHTS": {"legacy": 1.0}, "SKILL_VARIATIONS": {}}
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "professional_profile.json").write_text("{invalid", encoding="utf-8")
            loaded = load_profile_config(directory, fallback=fallback)

        self.assertFalse(loaded["loaded_from_files"])
        self.assertEqual(loaded["SKILL_WEIGHTS"], {"legacy": 1.0})

    def test_weights_are_normalized(self):
        weights = load_profile_config()["SKILL_WEIGHTS"]

        self.assertAlmostEqual(sum(weights.values()), 1.0, places=10)
        self.assertGreater(weights["llm_applications"], weights["cicd"])

    def test_ontology_aliases_reach_skill_variations(self):
        variations = load_profile_config()["SKILL_VARIATIONS"]

        self.assertIn("modelos de linguagem", variations["llm_applications"])
        self.assertIn("agentes de ia", variations["ai_agents"])
        self.assertIn("sistema de recomendação", variations["recommendation_systems"])

    def test_career_matcher_remains_compatible(self):
        matcher = CareerMatcher(Config())

        result = matcher.calculate_match(
            "Construção de aplicações com modelos de linguagem, RAG e APIs.",
            "Applied AI Engineer",
        )

        self.assertGreater(result["score"], 0)
        self.assertIn("llm_applications", result["matches"])
        self.assertIn(result["level"], {"💚 Alta", "💛 Média", "💔 Baixa"})


if __name__ == "__main__":
    unittest.main()
