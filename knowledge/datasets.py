"""Inspectable JSONL dataset IO for canonical knowledge records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import CanonicalEntity, CanonicalRelation, ConceptType, KnowledgeDataset


class DatasetExistsError(FileExistsError):
    """Raised when a versioned normalized output would be overwritten."""


def _write_jsonl(path: Path, values: Iterable[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def write_dataset(
    dataset: KnowledgeDataset,
    output_directory: str | Path,
    metadata: dict | None = None,
) -> Path:
    output = Path(output_directory)
    if output.exists() and any(output.iterdir()):
        raise DatasetExistsError(f"normalized dataset already exists: {output}")
    output.mkdir(parents=True, exist_ok=True)

    occupations = sorted(
        (entity for entity in dataset.entities
         if entity.concept_type in {ConceptType.OCCUPATION, ConceptType.OCCUPATION_GROUP}),
        key=lambda item: item.internal_id,
    )
    concepts = sorted(
        (entity for entity in dataset.entities
         if entity.concept_type not in {ConceptType.OCCUPATION, ConceptType.OCCUPATION_GROUP}),
        key=lambda item: item.internal_id,
    )
    relations = sorted(
        dataset.relations,
        key=lambda item: (item.source.value, item.subject, item.predicate, item.object),
    )
    try:
        _write_jsonl(output / "concepts.jsonl", (item.to_dict() for item in concepts))
        _write_jsonl(output / "occupations.jsonl", (item.to_dict() for item in occupations))
        _write_jsonl(output / "relations.jsonl", (item.to_dict() for item in relations))
        manifest = {
            "schema_version": "knowledge-canonical-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "counts": {
                "concepts": len(concepts),
                "occupations": len(occupations),
                "relations": len(relations),
            },
            "metadata": metadata or {},
        }
        (output / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output
    except Exception:
        for name in ("concepts.jsonl", "occupations.jsonl", "relations.jsonl", "manifest.json"):
            (output / name).unlink(missing_ok=True)
        raise


def load_dataset(*directories: str | Path) -> KnowledgeDataset:
    entities: list[CanonicalEntity] = []
    relations: list[CanonicalRelation] = []
    for directory in directories:
        root = Path(directory)
        for filename in ("concepts.jsonl", "occupations.jsonl"):
            with (root / filename).open("r", encoding="utf-8") as stream:
                entities.extend(CanonicalEntity.from_dict(json.loads(line)) for line in stream if line.strip())
        with (root / "relations.jsonl").open("r", encoding="utf-8") as stream:
            relations.extend(CanonicalRelation.from_dict(json.loads(line)) for line in stream if line.strip())
    return KnowledgeDataset.build(entities, relations)
