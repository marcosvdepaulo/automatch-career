"""Immutable raw snapshot storage with reproducibility manifests."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import KnowledgeSource


class SnapshotExistsError(FileExistsError):
    """Raised instead of mutating an existing raw snapshot."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class SnapshotManifest:
    source: KnowledgeSource
    version: str
    acquired_at: str
    files: tuple[dict[str, str | int], ...]

    def to_dict(self) -> dict:
        return {
            "source": self.source.value,
            "version": self.version,
            "acquired_at": self.acquired_at,
            "files": list(self.files),
        }


class SnapshotStore:
    def __init__(self, raw_root: str | Path = "knowledge/raw") -> None:
        self.raw_root = Path(raw_root)

    def create_from_directory(
        self,
        source: KnowledgeSource | str,
        version: str,
        input_directory: str | Path,
        acquired_at: datetime | None = None,
    ) -> Path:
        source = KnowledgeSource(source)
        version = version.strip()
        if not version or version in {".", ".."} or "/" in version or "\\" in version:
            raise ValueError("version must be a safe, non-empty directory name")
        origin = Path(input_directory)
        files = tuple(sorted(path for path in origin.rglob("*") if path.is_file()))
        if not files:
            raise ValueError(f"no source files found in {origin}")

        destination = self.raw_root / source.value / version
        if destination.exists():
            raise SnapshotExistsError(
                f"raw snapshot already exists and is immutable: {destination}"
            )
        destination.mkdir(parents=True)
        try:
            manifest_files: list[dict[str, str | int]] = []
            for source_file in files:
                relative = source_file.relative_to(origin)
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_file, target)
                manifest_files.append({
                    "path": relative.as_posix(),
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                })
            timestamp = acquired_at or datetime.now(timezone.utc)
            manifest = SnapshotManifest(
                source=source,
                version=version,
                acquired_at=timestamp.astimezone(timezone.utc).isoformat(),
                files=tuple(manifest_files),
            )
            (destination / "manifest.json").write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return destination
        except Exception:
            # The destination did not exist before this operation, so cleaning a
            # failed partial write cannot destroy a previously accepted snapshot.
            shutil.rmtree(destination, ignore_errors=True)
            raise

    def verify(self, snapshot_directory: str | Path) -> SnapshotManifest:
        directory = Path(snapshot_directory)
        manifest_data = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        manifest = SnapshotManifest(
            source=KnowledgeSource(manifest_data["source"]),
            version=manifest_data["version"],
            acquired_at=manifest_data["acquired_at"],
            files=tuple(manifest_data["files"]),
        )
        for item in manifest.files:
            path = directory / str(item["path"])
            if not path.is_file() or path.stat().st_size != item["size"]:
                raise ValueError(f"snapshot file missing or changed: {path}")
            if sha256_file(path) != item["sha256"]:
                raise ValueError(f"snapshot checksum mismatch: {path}")
        return manifest
