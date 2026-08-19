"""ESCO CSV adapter preserving official concept URIs."""

from __future__ import annotations

import re
from pathlib import Path

from knowledge.models import (
    CanonicalEntity,
    CanonicalRelation,
    ConceptType,
    KnowledgeDataset,
    KnowledgeSource,
    canonical_id,
)

from ._tabular import get_value, read_rows, source_record


def _labels(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        label.strip() for label in re.split(r"[\n;|]", value) if label.strip()
    ))


def _esco_type(row: dict, default: ConceptType) -> ConceptType:
    concept_value = get_value(row, "concept type", "conceptType").casefold()
    skill_value = get_value(row, "skill type", "skillType").casefold()
    if concept_value in {"og", "occupation group", "occupationgroup"}:
        return ConceptType.OCCUPATION_GROUP
    if concept_value in {"sg", "skill group", "skillgroup"}:
        return ConceptType.SKILL_GROUP
    if "knowledge" in skill_value:
        return ConceptType.KNOWLEDGE
    return default


class EscoImporter:
    """Convert an official ESCO CSV snapshot to canonical entities/relations."""

    source = KnowledgeSource.ESCO

    def import_snapshot(self, snapshot_directory: str | Path) -> KnowledgeDataset:
        root = Path(snapshot_directory)
        entities: list[CanonicalEntity] = []
        relations: list[CanonicalRelation] = []

        source_files = sorted(
            path for path in root.rglob("*")
            if path.is_file() and path.name != "manifest.json"
            and path.suffix.casefold() in {".csv", ".txt", ".tsv", ".json"}
        )
        for path in source_files:
            stem = re.sub(r"[^a-z]", "", path.stem.casefold())
            if "occupationskillrelations" in stem:
                relations.extend(self._occupation_skill_relations(path))
            elif "broaderrelations" in stem:
                relations.extend(self._broader_relations(path))
            elif "skillskillrelations" in stem:
                relations.extend(self._skill_relations(path))
            elif stem.startswith("occupations") or stem.startswith("iscogroups"):
                default = ConceptType.OCCUPATION_GROUP if stem.startswith("iscogroups") else ConceptType.OCCUPATION
                entities.extend(self._entities(path, default))
            elif stem.startswith("skills") and "hierarchy" not in stem:
                entities.extend(self._entities(path, ConceptType.SKILL))
            elif stem.startswith("skillgroups"):
                entities.extend(self._entities(path, ConceptType.SKILL_GROUP))

        if not entities:
            raise ValueError(f"no supported ESCO entity files found in {root}")
        return KnowledgeDataset.build(entities, relations)

    def _entities(self, path: Path, default_type: ConceptType) -> list[CanonicalEntity]:
        result = []
        for row in read_rows(path):
            uri = get_value(row, "concept uri", "conceptUri", "uri")
            label = get_value(row, "preferred label", "preferredLabel", "concept PT", "title")
            if not uri or not label:
                raise ValueError(f"ESCO row in {path.name} lost concept URI or label")
            result.append(CanonicalEntity(
                internal_id=canonical_id(self.source, uri),
                source=self.source,
                source_uri=uri,
                concept_type=_esco_type(row, default_type),
                preferred_label=label,
                alternative_labels=_labels(get_value(row, "alternative labels", "altLabels")),
                description=get_value(row, "description", "definition", "scopeNote") or None,
                metadata={"source_file": path.name, "source_record": source_record(row)},
            ))
        return result

    def _occupation_skill_relations(self, path: Path) -> list[CanonicalRelation]:
        result = []
        for row in read_rows(path):
            occupation = get_value(row, "occupation URI", "occupationUri")
            skill = get_value(row, "skill URI", "skillUri")
            predicate = get_value(row, "relation type", "relationType") or "related_skill"
            if not occupation or not skill:
                raise ValueError(f"ESCO relation in {path.name} lost an official URI")
            result.append(CanonicalRelation(
                canonical_id(self.source, occupation), predicate,
                canonical_id(self.source, skill), self.source,
                {"source_file": path.name, "source_record": source_record(row)},
            ))
        return result

    def _broader_relations(self, path: Path) -> list[CanonicalRelation]:
        result = []
        for row in read_rows(path):
            subject = get_value(row, "concept URI", "conceptUri", "narrower URI", "narrowerUri")
            broader = get_value(row, "broader URI", "broaderUri", "broader concept URI")
            if not subject or not broader:
                raise ValueError(f"ESCO broader relation in {path.name} lost an official URI")
            result.append(CanonicalRelation(
                canonical_id(self.source, subject), "broader",
                canonical_id(self.source, broader), self.source,
                {"source_file": path.name, "source_record": source_record(row)},
            ))
        return result

    def _skill_relations(self, path: Path) -> list[CanonicalRelation]:
        result = []
        for row in read_rows(path):
            subject = get_value(row, "skill URI", "skillUri", "subject URI", "subjectUri")
            related = get_value(row, "related skill URI", "relatedSkillUri", "object URI", "objectUri")
            predicate = get_value(row, "relation type", "relationType") or "related_skill"
            if not subject or not related:
                raise ValueError(f"ESCO skill relation in {path.name} lost an official URI")
            result.append(CanonicalRelation(
                canonical_id(self.source, subject), predicate,
                canonical_id(self.source, related), self.source,
                {"source_file": path.name, "source_record": source_record(row)},
            ))
        return result
