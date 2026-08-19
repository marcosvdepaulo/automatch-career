"""Reproducible external knowledge acquisition and preparation layer.

This package intentionally has no dependency on AutoMatch matching/domain modules.
"""

from .models import (
    CanonicalEntity,
    CanonicalRelation,
    ConceptType,
    KnowledgeDataset,
    KnowledgeSource,
)

__all__ = [
    "CanonicalEntity",
    "CanonicalRelation",
    "ConceptType",
    "KnowledgeDataset",
    "KnowledgeSource",
]
