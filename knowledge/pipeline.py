"""Explicit acquisition/normalization orchestration for each source."""

from __future__ import annotations

from pathlib import Path

from .datasets import write_dataset
from .models import KnowledgeSource
from .snapshots import SnapshotStore, sha256_file
from .sources import EscoImporter, OnetImporter


def normalize_esco_snapshot(
    version: str,
    raw_root: str | Path = "knowledge/raw",
    normalized_root: str | Path = "knowledge/normalized",
) -> Path:
    return _normalize(
        KnowledgeSource.ESCO, version, EscoImporter(), Path(raw_root), Path(normalized_root)
    )


def normalize_onet_snapshot(
    version: str,
    raw_root: str | Path = "knowledge/raw",
    normalized_root: str | Path = "knowledge/normalized",
) -> Path:
    return _normalize(
        KnowledgeSource.ONET, version, OnetImporter(), Path(raw_root), Path(normalized_root)
    )


def _normalize(source, version, importer, raw_root: Path, normalized_root: Path) -> Path:
    snapshot = raw_root / source.value / version
    destination = normalized_root / source.value / version
    if destination.resolve().is_relative_to(raw_root.resolve()):
        raise ValueError("normalized output cannot be written inside the immutable raw directory")
    manifest = SnapshotStore(raw_root).verify(snapshot)
    dataset = importer.import_snapshot(snapshot)
    return write_dataset(dataset, destination, metadata={
        "source": source.value,
        "source_version": manifest.version,
        "raw_manifest_sha256": sha256_file(snapshot / "manifest.json"),
        "raw_snapshot": snapshot.as_posix(),
    })
