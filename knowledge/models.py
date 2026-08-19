"""Canonical, source-faithful intermediate knowledge models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class KnowledgeValidationError(ValueError):
    """Raised when normalization would lose identity or provenance."""


class KnowledgeSource(StrEnum):
    ESCO = "esco"
    ONET = "onet"


class ConceptType(StrEnum):
    OCCUPATION = "occupation"
    SKILL = "skill"
    KNOWLEDGE = "knowledge"
    TECHNOLOGY = "technology"
    TOOL = "tool"
    WORK_ACTIVITY = "work_activity"
    OCCUPATION_GROUP = "occupation_group"
    SKILL_GROUP = "skill_group"
    OTHER = "other"


def canonical_id(source: KnowledgeSource, source_identity: str) -> str:
    identity = source_identity.strip()
    if not identity:
        raise KnowledgeValidationError("source identity cannot be empty")
    return f"{source.value}:{identity}"


@dataclass(frozen=True)
class CanonicalEntity:
    internal_id: str
    source: KnowledgeSource
    concept_type: ConceptType
    preferred_label: str
    source_uri: str | None = None
    source_id: str | None = None
    alternative_labels: tuple[str, ...] = ()
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_identity = self.source_uri if self.source is KnowledgeSource.ESCO else self.source_id
        if not source_identity or not source_identity.strip():
            required = "source_uri" if self.source is KnowledgeSource.ESCO else "source_id"
            raise KnowledgeValidationError(f"{self.source.value} entity requires {required}")
        expected = canonical_id(self.source, source_identity)
        if self.internal_id != expected:
            raise KnowledgeValidationError(
                f"internal_id must be derived from the preserved source identity: {expected}"
            )
        if not self.preferred_label.strip():
            raise KnowledgeValidationError("preferred_label cannot be empty")
        if self.source is KnowledgeSource.ESCO and not self.source_uri.startswith(("http://", "https://")):
            raise KnowledgeValidationError("ESCO source_uri must be an absolute URI")
        labels = tuple(dict.fromkeys(label.strip() for label in self.alternative_labels if label.strip()))
        object.__setattr__(self, "alternative_labels", labels)
        object.__setattr__(self, "metadata", deepcopy(self.metadata))

    @property
    def source_identity(self) -> str:
        return self.source_uri if self.source is KnowledgeSource.ESCO else self.source_id  # type: ignore[return-value]

    def to_dict(self) -> dict[str, Any]:
        return {
            "internal_id": self.internal_id,
            "source": self.source.value,
            "source_uri": self.source_uri,
            "source_id": self.source_id,
            "concept_type": self.concept_type.value,
            "preferred_label": self.preferred_label,
            "alternative_labels": list(self.alternative_labels),
            "description": self.description,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CanonicalEntity:
        return cls(
            internal_id=value["internal_id"],
            source=KnowledgeSource(value["source"]),
            source_uri=value.get("source_uri"),
            source_id=value.get("source_id"),
            concept_type=ConceptType(value["concept_type"]),
            preferred_label=value["preferred_label"],
            alternative_labels=tuple(value.get("alternative_labels", ())),
            description=value.get("description"),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True)
class CanonicalRelation:
    subject: str
    predicate: str
    object: str
    source: KnowledgeSource
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        prefix = f"{self.source.value}:"
        if not self.subject.startswith(prefix) or not self.object.startswith(prefix):
            raise KnowledgeValidationError(
                "relation endpoints must retain canonical identities from the same source"
            )
        if not self.predicate.strip():
            raise KnowledgeValidationError("relation predicate cannot be empty")
        object.__setattr__(self, "metadata", deepcopy(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "source": self.source.value,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CanonicalRelation:
        return cls(
            subject=value["subject"],
            predicate=value["predicate"],
            object=value["object"],
            source=KnowledgeSource(value["source"]),
            metadata=value.get("metadata", {}),
        )


def _merge_metadata(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(left)
    for key, value in right.items():
        if key not in merged:
            merged[key] = deepcopy(value)
        elif merged[key] != value:
            existing = merged[key] if isinstance(merged[key], list) else [merged[key]]
            additions = value if isinstance(value, list) else [value]
            unique = []
            for item in (*existing, *additions):
                if not any(item == accepted for accepted in unique):
                    unique.append(deepcopy(item))
            merged[key] = unique
    return merged


def deduplicate_entities(entities: Iterable[CanonicalEntity]) -> tuple[CanonicalEntity, ...]:
    """Merge source-identical entities without ever merging by label."""

    merged: dict[str, CanonicalEntity] = {}
    for entity in entities:
        current = merged.get(entity.internal_id)
        if current is None:
            merged[entity.internal_id] = entity
            continue
        if (
            current.source != entity.source
            or current.source_identity != entity.source_identity
            or current.concept_type != entity.concept_type
        ):
            raise KnowledgeValidationError(
                f"conflicting entities share internal identity {entity.internal_id}"
            )
        alternatives = tuple(dict.fromkeys(
            (*current.alternative_labels, *entity.alternative_labels,
             *(() if current.preferred_label == entity.preferred_label else (entity.preferred_label,)))
        ))
        merged[entity.internal_id] = CanonicalEntity(
            internal_id=current.internal_id,
            source=current.source,
            source_uri=current.source_uri,
            source_id=current.source_id,
            concept_type=current.concept_type,
            preferred_label=current.preferred_label,
            alternative_labels=alternatives,
            description=current.description or entity.description,
            metadata=_merge_metadata(current.metadata, entity.metadata),
        )
    return tuple(merged[key] for key in sorted(merged))


@dataclass(frozen=True)
class KnowledgeDataset:
    entities: tuple[CanonicalEntity, ...]
    relations: tuple[CanonicalRelation, ...]

    def __post_init__(self) -> None:
        ids = {entity.internal_id for entity in self.entities}
        if len(ids) != len(self.entities):
            raise KnowledgeValidationError("dataset contains duplicate entity identities")
        missing = sorted({endpoint for relation in self.relations
                          for endpoint in (relation.subject, relation.object) if endpoint not in ids})
        if missing:
            raise KnowledgeValidationError(f"relations reference missing entities: {missing[:3]}")

    @classmethod
    def build(
        cls,
        entities: Iterable[CanonicalEntity],
        relations: Iterable[CanonicalRelation],
    ) -> KnowledgeDataset:
        unique_entities = deduplicate_entities(entities)
        unique_relations: dict[tuple[str, str, str, str], CanonicalRelation] = {}
        for relation in relations:
            # Multiple O*NET rating rows describe the same semantic edge. Preserve
            # every rating in metadata instead of emitting duplicate graph edges.
            key = (relation.source.value, relation.subject, relation.predicate, relation.object)
            existing = unique_relations.get(key)
            if existing is None:
                unique_relations[key] = relation
            else:
                unique_relations[key] = CanonicalRelation(
                    relation.subject,
                    relation.predicate,
                    relation.object,
                    relation.source,
                    _merge_metadata(existing.metadata, relation.metadata),
                )
        return cls(
            unique_entities,
            tuple(unique_relations[key] for key in sorted(unique_relations)),
        )
