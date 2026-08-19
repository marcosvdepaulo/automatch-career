"""Declarative, seed-based and bounded occupational scope expansion."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import ConceptType, KnowledgeDataset, KnowledgeSource, canonical_id


@dataclass(frozen=True)
class ScopeDefinition:
    scope_id: str
    label: str
    esco_seeds: tuple[str, ...]
    onet_seeds: tuple[str, ...]
    related_occupation_depth: int = 0

    def __post_init__(self) -> None:
        if not self.scope_id or not self.label:
            raise ValueError("scope id and label are required")
        if self.related_occupation_depth < 0:
            raise ValueError("scope depth cannot be negative")
        if not self.esco_seeds and not self.onet_seeds:
            raise ValueError(f"scope {self.scope_id} requires explicit occupation seeds")
        for uri in self.esco_seeds:
            if not re.fullmatch(r"https?://data\.europa\.eu/esco/occupation/[^\s]+", uri):
                raise ValueError(f"invalid ESCO occupation URI in {self.scope_id}: {uri}")
        for source_id in self.onet_seeds:
            if not re.fullmatch(r"\d{2}-\d{4}\.\d{2}", source_id):
                raise ValueError(f"invalid O*NET-SOC code in {self.scope_id}: {source_id}")

    @property
    def canonical_seeds(self) -> tuple[str, ...]:
        values = [canonical_id(KnowledgeSource.ESCO, value) for value in self.esco_seeds]
        values.extend(canonical_id(KnowledgeSource.ONET, value) for value in self.onet_seeds)
        return tuple(values)


def load_scope_definitions(path: str | Path) -> tuple[ScopeDefinition, ...]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    scopes = []
    seen = set()
    for value in document.get("scopes", []):
        scope_id = value["id"]
        if scope_id in seen:
            raise ValueError(f"duplicate scope id: {scope_id}")
        seen.add(scope_id)
        seeds = value.get("seeds", {})
        scopes.append(ScopeDefinition(
            scope_id=scope_id,
            label=value["label"],
            esco_seeds=tuple(seeds.get("esco", ())),
            onet_seeds=tuple(seeds.get("onet", ())),
            related_occupation_depth=int(value.get("related_occupation_depth", 0)),
        ))
    if not scopes:
        raise ValueError("scope configuration contains no scopes")
    return tuple(scopes)


class ScopeExpander:
    RELATED_OCCUPATION_PREDICATES = frozenset({
        "related_occupation", "broader", "broader_occupation", "narrower_occupation",
    })

    def __init__(self, dataset: KnowledgeDataset) -> None:
        self.dataset = dataset
        self.entities = {entity.internal_id: entity for entity in dataset.entities}

    def expand(
        self,
        definition: ScopeDefinition,
        depth: int | None = None,
    ) -> KnowledgeDataset:
        requested_depth = definition.related_occupation_depth if depth is None else depth
        if requested_depth < 0:
            raise ValueError("scope depth cannot be negative")
        missing = sorted(set(definition.canonical_seeds) - self.entities.keys())
        if missing:
            raise ValueError(f"scope {definition.scope_id} has seeds absent from dataset: {missing}")
        non_occupations = {
            entity.internal_id for entity in self.dataset.entities
            if entity.concept_type not in {ConceptType.OCCUPATION, ConceptType.OCCUPATION_GROUP}
        }
        occupation_ids = set(self.entities) - non_occupations
        occupations = set(definition.canonical_seeds)
        frontier = set(occupations)
        for _ in range(requested_depth):
            neighbors = set()
            for relation in self.dataset.relations:
                if relation.predicate not in self.RELATED_OCCUPATION_PREDICATES:
                    continue
                if relation.subject in frontier and relation.object in occupation_ids:
                    neighbors.add(relation.object)
                if relation.object in frontier and relation.subject in occupation_ids:
                    neighbors.add(relation.subject)
            frontier = neighbors - occupations
            occupations.update(frontier)

        included = set(occupations)
        for relation in self.dataset.relations:
            if relation.subject in occupations and relation.object in non_occupations:
                included.add(relation.object)
            elif relation.object in occupations and relation.subject in non_occupations:
                included.add(relation.subject)

        entities = [self.entities[entity_id] for entity_id in sorted(included)]
        relations = [
            relation for relation in self.dataset.relations
            if relation.subject in included and relation.object in included
        ]
        return KnowledgeDataset.build(entities, relations)
