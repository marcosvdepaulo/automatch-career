"""Command line interface for the reproducible knowledge pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .datasets import load_dataset, write_dataset
from .models import KnowledgeSource
from .pipeline import normalize_esco_snapshot, normalize_onet_snapshot
from .scopes import ScopeExpander, load_scope_definitions
from .snapshots import SnapshotStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m knowledge")
    commands = parser.add_subparsers(dest="command", required=True)

    acquire = commands.add_parser("acquire", help="copy a local official export into immutable raw storage")
    acquire.add_argument("--source", choices=[item.value for item in KnowledgeSource], required=True)
    acquire.add_argument("--version", required=True)
    acquire.add_argument("--input", required=True, help="directory containing the untouched source export")
    acquire.add_argument("--raw-root", default="knowledge/raw")
    acquire.add_argument("--acquired-at", help="optional ISO-8601 acquisition timestamp")

    normalize = commands.add_parser("normalize", help="normalize one verified raw snapshot")
    normalize.add_argument("--source", choices=[item.value for item in KnowledgeSource], required=True)
    normalize.add_argument("--version", required=True)
    normalize.add_argument("--raw-root", default="knowledge/raw")
    normalize.add_argument("--normalized-root", default="knowledge/normalized")

    scopes = commands.add_parser("build-scopes", help="build bounded subgraphs from explicit seeds")
    scopes.add_argument("--dataset", action="append", required=True,
                        help="normalized source directory; repeat for ESCO and O*NET")
    scopes.add_argument("--config", default="knowledge/scopes/occupational_scopes.json")
    scopes.add_argument("--output-root", default="knowledge/normalized/scopes")
    scopes.add_argument("--raw-root", default="knowledge/raw")
    scopes.add_argument("--build-id", required=True, help="immutable identifier for this scope build")
    scopes.add_argument("--depth", type=int, help="override every scope's configured depth")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "acquire":
        acquired_at = datetime.fromisoformat(args.acquired_at) if args.acquired_at else None
        destination = SnapshotStore(args.raw_root).create_from_directory(
            args.source, args.version, args.input, acquired_at
        )
        print(f"raw snapshot: {destination}")
        return 0
    if args.command == "normalize":
        function = normalize_esco_snapshot if args.source == "esco" else normalize_onet_snapshot
        destination = function(args.version, args.raw_root, args.normalized_root)
        print(f"normalized dataset: {destination}")
        return 0

    dataset = load_dataset(*args.dataset)
    expander = ScopeExpander(dataset)
    if Path(args.build_id).name != args.build_id or args.build_id in {".", ".."}:
        raise ValueError("build-id must be a safe directory name")
    build_root = Path(args.output_root) / args.build_id
    if build_root.resolve().is_relative_to(Path(args.raw_root).resolve()):
        raise ValueError("scope output cannot be written inside the immutable raw directory")
    expanded = [
        (definition, expander.expand(definition, args.depth))
        for definition in load_scope_definitions(args.config)
    ]
    for definition, scoped in expanded:
        destination = write_dataset(scoped, build_root / definition.scope_id, metadata={
            "scope_id": definition.scope_id,
            "scope_label": definition.label,
            "seeds": list(definition.canonical_seeds),
            "related_occupation_depth": (
                definition.related_occupation_depth if args.depth is None else args.depth
            ),
            "input_datasets": list(args.dataset),
        })
        print(f"scope {definition.scope_id}: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
