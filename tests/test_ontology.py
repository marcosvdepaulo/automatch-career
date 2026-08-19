import json
import tempfile
import unittest
from pathlib import Path
from ontology import load_ontology

class OntologyTests(unittest.TestCase):
    def test_global_ontology_has_no_candidate_priorities(self):
        ontology = load_ontology()
        self.assertTrue(ontology.skills)
        self.assertTrue(ontology.role_families)
        self.assertTrue(all("priority" not in role for role in ontology.role_families))

    def test_rejects_personal_priority_in_role_family(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path("profile/skills_ontology.json").read_text(encoding="utf-8-sig")
            Path(directory, "skills_ontology.json").write_text(source, encoding="utf-8")
            Path(directory, "role_families.json").write_text(json.dumps({"role_families": [{"id":"x","priority":1}]}), encoding="utf-8")
            with self.assertRaises(ValueError): load_ontology(directory)

if __name__ == "__main__": unittest.main()
