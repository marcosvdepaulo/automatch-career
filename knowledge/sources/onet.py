"""O*NET tabular adapter preserving O*NET-SOC and Content Model IDs."""

from __future__ import annotations

import re
from collections import defaultdict
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


class OnetImporter:
    """Convert official O*NET text/CSV/JSON files to canonical records."""

    source = KnowledgeSource.ONET

    _CONTENT_FILES = {
        "skills": (ConceptType.SKILL, "requires_skill"),
        "essentialskills": (ConceptType.SKILL, "requires_essential_skill"),
        "transferableskills": (ConceptType.SKILL, "requires_transferable_skill"),
        "knowledge": (ConceptType.KNOWLEDGE, "requires_knowledge"),
        "workactivities": (ConceptType.WORK_ACTIVITY, "performs_work_activity"),
    }
    _COMMODITY_FILES = {
        "technologyskills": (ConceptType.TECHNOLOGY, "uses_technology"),
        "softwareskills": (ConceptType.TECHNOLOGY, "uses_technology"),
        "toolsused": (ConceptType.TOOL, "uses_tool"),
    }

    def import_snapshot(self, snapshot_directory: str | Path) -> KnowledgeDataset:
        root = Path(snapshot_directory)
        entities: list[CanonicalEntity] = []
        relations: list[CanonicalRelation] = []
        files = sorted(
            path for path in root.rglob("*")
            if path.is_file() and path.name != "manifest.json"
            and path.suffix.casefold() in {".csv", ".txt", ".tsv", ".json"}
        )
        content_reference = self._content_reference(files)
        alternate_titles = self._alternate_titles(files)
        for path in files:
            stem = re.sub(r"[^a-z]", "", path.stem.casefold())
            if stem == "occupationdata":
                entities.extend(self._occupations(path, alternate_titles))
            elif stem in self._CONTENT_FILES:
                new_entities, new_relations = self._content(
                    path, *self._CONTENT_FILES[stem], content_reference
                )
                entities.extend(new_entities)
                relations.extend(new_relations)
            elif stem in self._COMMODITY_FILES:
                new_entities, new_relations = self._commodities(path, *self._COMMODITY_FILES[stem])
                entities.extend(new_entities)
                relations.extend(new_relations)
            elif stem == "relatedoccupations":
                relations.extend(self._related_occupations(path))

        if not entities:
            raise ValueError(f"no supported O*NET entity files found in {root}")
        return KnowledgeDataset.build(entities, relations)

    def _content_reference(self, files: list[Path]) -> dict[str, dict[str, str]]:
        references = {}
        for path in files:
            stem = re.sub(r"[^a-z]", "", path.stem.casefold())
            if stem != "contentmodelreference":
                continue
            for row in read_rows(path):
                element_id = get_value(row, "Element ID", "element_id")
                if element_id:
                    references[element_id] = {
                        "label": get_value(row, "Element Name", "element_name"),
                        "description": get_value(row, "Description", "description"),
                    }
        return references

    def _alternate_titles(self, files: list[Path]) -> dict[str, tuple[str, ...]]:
        titles: dict[str, list[str]] = defaultdict(list)
        supported = {"alternatetitles", "jobtitles", "sampleofreportedtitles"}
        for path in files:
            stem = re.sub(r"[^a-z]", "", path.stem.casefold())
            if stem not in supported:
                continue
            for row in read_rows(path):
                occupation_id = get_value(row, "O*NET-SOC Code", "onetsoc_code")
                title = get_value(row, "Alternate Title", "Job Title", "Reported Job Title")
                if occupation_id and title and title not in titles[occupation_id]:
                    titles[occupation_id].append(title)
        return {source_id: tuple(values) for source_id, values in titles.items()}

    def _occupations(
        self,
        path: Path,
        alternate_titles: dict[str, tuple[str, ...]],
    ) -> list[CanonicalEntity]:
        result = []
        for row in read_rows(path):
            source_id = get_value(row, "O*NET-SOC Code", "onetsoc_code")
            label = get_value(row, "Title", "title")
            if not source_id or not label:
                raise ValueError(f"O*NET occupation in {path.name} lost code or title")
            result.append(CanonicalEntity(
                internal_id=canonical_id(self.source, source_id),
                source=self.source,
                source_id=source_id,
                concept_type=ConceptType.OCCUPATION,
                preferred_label=label,
                alternative_labels=alternate_titles.get(source_id, ()),
                description=get_value(row, "Description", "description") or None,
                metadata={"source_file": path.name, "source_record": source_record(row)},
            ))
        return result

    def _content(
        self,
        path: Path,
        concept_type: ConceptType,
        predicate: str,
        content_reference: dict[str, dict[str, str]],
    ) -> tuple[list[CanonicalEntity], list[CanonicalRelation]]:
        entities = []
        relations = []
        for row in read_rows(path):
            occupation_id = get_value(row, "O*NET-SOC Code", "onetsoc_code")
            element_id = get_value(row, "Element ID", "element_id")
            reference = content_reference.get(element_id, {})
            element_name = get_value(row, "Element Name", "element_name") or reference.get("label", "")
            if not occupation_id or not element_id or not element_name:
                raise ValueError(f"O*NET content row in {path.name} lost an official ID")
            metadata = {"source_file": path.name, "source_record": source_record(row)}
            entities.append(CanonicalEntity(
                internal_id=canonical_id(self.source, element_id),
                source=self.source,
                source_id=element_id,
                concept_type=concept_type,
                preferred_label=element_name,
                description=reference.get("description") or None,
                metadata=metadata,
            ))
            relation_metadata = {
                "source_file": path.name,
                "scale_id": get_value(row, "Scale ID", "scale_id") or None,
                "data_value": get_value(row, "Data Value", "data_value") or None,
                "source_record": source_record(row),
            }
            relations.append(CanonicalRelation(
                canonical_id(self.source, occupation_id), predicate,
                canonical_id(self.source, element_id), self.source, relation_metadata,
            ))
        return entities, relations

    def _commodities(
        self,
        path: Path,
        concept_type: ConceptType,
        predicate: str,
    ) -> tuple[list[CanonicalEntity], list[CanonicalRelation]]:
        entities = []
        relations = []
        for row in read_rows(path):
            occupation_id = get_value(row, "O*NET-SOC Code", "onetsoc_code")
            commodity_code = get_value(row, "Commodity Code", "commodity_code")
            commodity_title = get_value(row, "Commodity Title", "commodity_title")
            example = get_value(row, "Example", "example")
            if not occupation_id or not commodity_code:
                raise ValueError(
                    f"O*NET commodity row in {path.name} requires occupation and UNSPSC code; "
                    "labels are never used as identity"
                )
            source_id = f"UNSPSC:{commodity_code}"
            label = commodity_title or example
            if not label:
                raise ValueError(f"O*NET commodity row in {path.name} has no label")
            metadata = {"source_file": path.name, "source_record": source_record(row)}
            entities.append(CanonicalEntity(
                internal_id=canonical_id(self.source, source_id),
                source=self.source,
                source_id=source_id,
                concept_type=concept_type,
                preferred_label=label,
                alternative_labels=(example,) if example and example != label else (),
                metadata=metadata,
            ))
            relations.append(CanonicalRelation(
                canonical_id(self.source, occupation_id), predicate,
                canonical_id(self.source, source_id), self.source, metadata,
            ))
        return entities, relations

    def _related_occupations(self, path: Path) -> list[CanonicalRelation]:
        result = []
        for row in read_rows(path):
            subject = get_value(row, "O*NET-SOC Code", "onetsoc_code")
            related = get_value(row, "Related O*NET-SOC Code", "related_onetsoc_code")
            if not subject or not related:
                raise ValueError(f"O*NET related occupation in {path.name} lost an official code")
            result.append(CanonicalRelation(
                canonical_id(self.source, subject), "related_occupation",
                canonical_id(self.source, related), self.source,
                {"source_file": path.name, "source_record": source_record(row)},
            ))
        return result
