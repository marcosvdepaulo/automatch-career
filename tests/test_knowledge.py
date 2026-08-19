import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from knowledge.datasets import DatasetExistsError, load_dataset, write_dataset
from knowledge.models import (
    CanonicalEntity,
    CanonicalRelation,
    ConceptType,
    KnowledgeDataset,
    KnowledgeSource,
    KnowledgeValidationError,
    canonical_id,
    deduplicate_entities,
)
from knowledge.pipeline import normalize_esco_snapshot
from knowledge.scopes import ScopeDefinition, ScopeExpander, load_scope_definitions
from knowledge.snapshots import SnapshotExistsError, SnapshotStore
from knowledge.sources import EscoImporter, OnetImporter


ESCO_OCCUPATION = "http://data.europa.eu/esco/occupation/seed"
ESCO_SKILL = "http://data.europa.eu/esco/skill/python"


def onet_entity(source_id, concept_type, label):
    return CanonicalEntity(
        canonical_id(KnowledgeSource.ONET, source_id),
        KnowledgeSource.ONET,
        concept_type,
        label,
        source_id=source_id,
    )


class KnowledgeModelTests(unittest.TestCase):
    def test_identity_and_provenance_are_mandatory(self):
        with self.assertRaises(KnowledgeValidationError):
            CanonicalEntity(
                "esco:missing", KnowledgeSource.ESCO, ConceptType.SKILL, "Python"
            )
        with self.assertRaises(KnowledgeValidationError):
            CanonicalEntity(
                "esco:label-derived", KnowledgeSource.ESCO, ConceptType.SKILL, "Python",
                source_uri=ESCO_SKILL,
            )

    def test_deduplication_uses_source_identity_not_labels(self):
        first = onet_entity("2.A.1", ConceptType.SKILL, "Programming")
        same_label_other_id = onet_entity("2.A.2", ConceptType.SKILL, "Programming")
        duplicate = CanonicalEntity(
            first.internal_id, first.source, first.concept_type, "Programming",
            source_id=first.source_id, alternative_labels=("Coding",), metadata={"release": "30.3"},
        )
        merged = deduplicate_entities((first, same_label_other_id, duplicate))
        self.assertEqual(len(merged), 2)
        self.assertIn("Coding", next(item for item in merged if item.source_id == "2.A.1").alternative_labels)


class SnapshotTests(unittest.TestCase):
    def test_snapshot_is_a_copy_with_manifest_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            incoming.mkdir()
            source_file = incoming / "Occupation Data.txt"
            source_file.write_text("original", encoding="utf-8")
            store = SnapshotStore(root / "raw")
            acquired = datetime(2026, 8, 19, tzinfo=timezone.utc)
            snapshot = store.create_from_directory("onet", "30.3", incoming, acquired)
            source_file.write_text("changed outside raw", encoding="utf-8")

            self.assertEqual((snapshot / "Occupation Data.txt").read_text(), "original")
            manifest = store.verify(snapshot)
            self.assertEqual(manifest.source, KnowledgeSource.ONET)
            self.assertEqual(len(manifest.files[0]["sha256"]), 64)
            with self.assertRaises(SnapshotExistsError):
                store.create_from_directory("onet", "30.3", incoming)

    def test_checksum_detects_raw_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            incoming.mkdir()
            (incoming / "source.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            store = SnapshotStore(root / "raw")
            snapshot = store.create_from_directory("esco", "test", incoming)
            (snapshot / "source.csv").write_text("corrupted", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.verify(snapshot)


class ImporterTests(unittest.TestCase):
    def test_esco_importer_preserves_uri_types_labels_and_explicit_relation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "occupations_en.csv").write_text(
                "conceptUri,conceptType,preferredLabel,altLabels,description\n"
                f"{ESCO_OCCUPATION},OC,Software developer,Programmer;Coder,Writes software\n",
                encoding="utf-8",
            )
            (root / "skills_en.csv").write_text(
                "conceptUri,conceptType,skillType,preferredLabel,description\n"
                f"{ESCO_SKILL},SK,knowledge,Python programming,Python knowledge\n",
                encoding="utf-8",
            )
            (root / "occupationSkillRelations_en.csv").write_text(
                "occupationUri,relationType,skillUri\n"
                f"{ESCO_OCCUPATION},essentialSkill,{ESCO_SKILL}\n",
                encoding="utf-8",
            )
            dataset = EscoImporter().import_snapshot(root)

            occupation = next(item for item in dataset.entities if item.concept_type == ConceptType.OCCUPATION)
            knowledge = next(item for item in dataset.entities if item.concept_type == ConceptType.KNOWLEDGE)
            self.assertEqual(occupation.source_uri, ESCO_OCCUPATION)
            self.assertEqual(knowledge.source_uri, ESCO_SKILL)
            self.assertEqual(occupation.alternative_labels, ("Programmer", "Coder"))
            self.assertEqual(dataset.relations[0].predicate, "essentialSkill")

    def test_onet_importer_preserves_official_ids_and_source_categories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Occupation Data.txt").write_text(
                "O*NET-SOC Code\tTitle\tDescription\n15-1252.00\tSoftware Developers\tDevelop software\n",
                encoding="utf-8",
            )
            (root / "Job Titles.txt").write_text(
                "O*NET-SOC Code\tJob Title\n15-1252.00\tApplication Developer\n",
                encoding="utf-8",
            )
            (root / "Content Model Reference.txt").write_text(
                "Element ID\tElement Name\tDescription\n"
                "2.A.1.a\tProgramming\tWriting computer programs.\n",
                encoding="utf-8",
            )
            (root / "Skills.txt").write_text(
                "O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\n"
                "15-1252.00\t2.A.1.a\tProgramming\tIM\t4.5\n"
                "15-1252.00\t2.A.1.a\tProgramming\tLV\t5.0\n",
                encoding="utf-8",
            )
            (root / "Knowledge.txt").write_text(
                "O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\n"
                "15-1252.00\t2.C.3.a\tComputers and Electronics\tIM\t5.0\n",
                encoding="utf-8",
            )
            (root / "Work Activities.txt").write_text(
                "O*NET-SOC Code\tElement ID\tElement Name\tScale ID\tData Value\n"
                "15-1252.00\t4.A.2.a\tAnalyzing Data\tIM\t4.0\n",
                encoding="utf-8",
            )
            dataset = OnetImporter().import_snapshot(root)
            by_id = {item.source_id: item for item in dataset.entities}

            self.assertEqual(by_id["15-1252.00"].concept_type, ConceptType.OCCUPATION)
            self.assertIn("Application Developer", by_id["15-1252.00"].alternative_labels)
            self.assertEqual(by_id["2.A.1.a"].concept_type, ConceptType.SKILL)
            self.assertEqual(by_id["2.A.1.a"].description, "Writing computer programs.")
            self.assertEqual(by_id["2.C.3.a"].concept_type, ConceptType.KNOWLEDGE)
            self.assertEqual(by_id["4.A.2.a"].concept_type, ConceptType.WORK_ACTIVITY)
            self.assertEqual({item.predicate for item in dataset.relations}, {
                "requires_skill", "requires_knowledge", "performs_work_activity"
            })
            skill_relation = next(item for item in dataset.relations if item.predicate == "requires_skill")
            self.assertEqual(skill_relation.metadata["scale_id"], ["IM", "LV"])
            self.assertEqual(len(skill_relation.metadata["source_record"]), 2)

    def test_onet_technology_requires_official_commodity_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Occupation Data.txt").write_text(
                "O*NET-SOC Code\tTitle\n15-1252.00\tSoftware Developers\n", encoding="utf-8"
            )
            (root / "Technology Skills.txt").write_text(
                "O*NET-SOC Code\tExample\tCommodity Code\tCommodity Title\n"
                "15-1252.00\tPython\t\tDevelopment software\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "labels are never used as identity"):
                OnetImporter().import_snapshot(root)


class DatasetAndScopeTests(unittest.TestCase):
    def setUp(self):
        self.seed = onet_entity("15-0001.00", ConceptType.OCCUPATION, "Seed")
        self.neighbor = onet_entity("15-0002.00", ConceptType.OCCUPATION, "Neighbor")
        self.distant = onet_entity("15-0003.00", ConceptType.OCCUPATION, "Distant")
        self.skill_one = onet_entity("2.A.1", ConceptType.SKILL, "One")
        self.skill_two = onet_entity("2.A.2", ConceptType.SKILL, "Two")
        self.skill_three = onet_entity("2.A.3", ConceptType.SKILL, "Three")
        self.dataset = KnowledgeDataset.build(
            (self.seed, self.neighbor, self.distant, self.skill_one, self.skill_two, self.skill_three),
            (
                CanonicalRelation(self.seed.internal_id, "broader", self.neighbor.internal_id, KnowledgeSource.ONET),
                CanonicalRelation(self.neighbor.internal_id, "related_occupation", self.distant.internal_id, KnowledgeSource.ONET),
                CanonicalRelation(self.seed.internal_id, "requires_skill", self.skill_one.internal_id, KnowledgeSource.ONET),
                CanonicalRelation(self.neighbor.internal_id, "requires_skill", self.skill_two.internal_id, KnowledgeSource.ONET),
                CanonicalRelation(self.distant.internal_id, "requires_skill", self.skill_three.internal_id, KnowledgeSource.ONET),
            ),
        )

    def test_jsonl_outputs_are_separate_inspectable_and_write_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dataset"
            write_dataset(self.dataset, output, {"source_version": "fixture"})
            self.assertEqual(len((output / "occupations.jsonl").read_text().splitlines()), 3)
            self.assertEqual(len((output / "concepts.jsonl").read_text().splitlines()), 3)
            relation = json.loads((output / "relations.jsonl").read_text().splitlines()[0])
            self.assertEqual(set(relation), {"subject", "predicate", "object", "source", "metadata"})
            self.assertEqual(load_dataset(output), self.dataset)
            with self.assertRaises(DatasetExistsError):
                write_dataset(self.dataset, output)

    def test_scope_expansion_depth_is_bounded_and_deterministic(self):
        definition = ScopeDefinition("test", "Test", (), ("15-0001.00",), 0)
        expander = ScopeExpander(self.dataset)
        depth_zero = expander.expand(definition)
        depth_one = expander.expand(definition, 1)

        self.assertEqual({item.source_id for item in depth_zero.entities}, {"15-0001.00", "2.A.1"})
        self.assertEqual(
            {item.source_id for item in depth_one.entities},
            {"15-0001.00", "15-0002.00", "2.A.1", "2.A.2"},
        )
        self.assertNotIn("15-0003.00", {item.source_id for item in depth_one.entities})
        self.assertEqual(depth_one, expander.expand(definition, 1))

    def test_checked_in_config_has_the_five_explicit_scopes(self):
        scopes = load_scope_definitions("knowledge/scopes/occupational_scopes.json")
        self.assertEqual({scope.scope_id for scope in scopes}, {
            "artificial_intelligence", "data", "cybersecurity",
            "software_engineering", "web_development",
        })
        self.assertTrue(all(scope.canonical_seeds for scope in scopes))

    def test_knowledge_package_does_not_import_matching_domain(self):
        forbidden = ("domain", "matcher", "profiling", "opportunity_parser")
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in Path("knowledge").rglob("*.py")
        )
        for module in forbidden:
            self.assertNotIn(f"import {module}", source)
            self.assertNotIn(f"from {module}", source)


class PipelineTests(unittest.TestCase):
    def test_normalization_reads_raw_and_writes_elsewhere(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            incoming = root / "incoming"
            incoming.mkdir()
            (incoming / "occupations_en.csv").write_text(
                "conceptUri,conceptType,preferredLabel\n"
                f"{ESCO_OCCUPATION},OC,Software developer\n", encoding="utf-8"
            )
            raw_root = root / "raw"
            snapshot = SnapshotStore(raw_root).create_from_directory("esco", "1.0", incoming)
            before = (snapshot / "occupations_en.csv").read_bytes()
            output = normalize_esco_snapshot("1.0", raw_root, root / "normalized")

            self.assertEqual((snapshot / "occupations_en.csv").read_bytes(), before)
            self.assertTrue((output / "occupations.jsonl").is_file())
            normalized_manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(normalized_manifest["metadata"]["source_version"], "1.0")
            self.assertEqual(len(normalized_manifest["metadata"]["raw_manifest_sha256"]), 64)
            with self.assertRaisesRegex(ValueError, "immutable raw"):
                normalize_esco_snapshot("1.0", raw_root, raw_root / "normalized")


if __name__ == "__main__":
    unittest.main()
