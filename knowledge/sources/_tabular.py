"""Small tabular parsing helpers shared by source-specific adapters."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Iterator


def normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def get_value(row: dict, *names: str) -> str:
    normalized = {normalized_key(str(key)): value for key, value in row.items()}
    for name in names:
        value = normalized.get(normalized_key(name))
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def read_rows(path: Path) -> Iterator[dict]:
    if path.suffix.casefold() == ".json":
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = value if isinstance(value, list) else value.get("rows", value.get("data", []))
        if not isinstance(rows, list):
            raise ValueError(f"expected a JSON array in {path}")
        for row in rows:
            if isinstance(row, dict):
                yield row
        return

    delimiter = "\t" if path.suffix.casefold() in {".txt", ".tsv"} else ","
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        if not reader.fieldnames:
            raise ValueError(f"source file has no header: {path}")
        yield from reader


def source_record(row: dict) -> dict[str, str]:
    return {str(key): str(value) for key, value in row.items()
            if value is not None and str(value).strip()}
