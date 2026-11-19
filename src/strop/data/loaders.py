"""Reading CSV and JSONL files into raw records."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strop.config import DatasetFormat
from strop.errors import DataError


@dataclass(frozen=True, slots=True)
class RawRecord:
    """One file record before validation. ``error`` is set when it could not be parsed."""

    number: int
    values: dict[str, Any]
    error: str | None = None


def file_hash(path: Path) -> str:
    """SHA-256 of the raw file bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_records(path: Path, fmt: DatasetFormat) -> tuple[tuple[str, ...], list[RawRecord]]:
    """Return the column names and every record of ``path``."""
    try:
        if fmt is DatasetFormat.CSV:
            return _read_csv(path)
        return _read_jsonl(path)
    except FileNotFoundError:
        raise DataError(f"dataset file not found: {path}") from None
    except UnicodeDecodeError as exc:
        raise DataError(f"{path.name} is not valid UTF-8 text: {exc.reason}") from exc


def _read_csv(path: Path) -> tuple[tuple[str, ...], list[RawRecord]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header or not any(name.strip() for name in header):
            raise DataError(f"{path.name} has no header row")
        columns = tuple(name.strip() for name in header)
        if len(set(columns)) != len(columns):
            raise DataError(f"{path.name} has duplicate column names in its header")
        # csv.reader yields an empty list for a blank line, such as a trailing newline at the
        # end of the file. Skip those the way JSONL does instead of reporting a bad row.
        filled = (cells for cells in reader if cells)
        records = [_csv_record(number, columns, cells) for number, cells in enumerate(filled, 1)]
    return columns, records


def _csv_record(number: int, columns: tuple[str, ...], cells: list[str]) -> RawRecord:
    if len(cells) != len(columns):
        return RawRecord(number, {}, f"has {len(cells)} fields, expected {len(columns)}")
    return RawRecord(number, dict(zip(columns, cells, strict=True)))


def _read_jsonl(path: Path) -> tuple[tuple[str, ...], list[RawRecord]]:
    columns: dict[str, None] = {}
    records = []
    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = _jsonl_record(number, line)
            columns.update(dict.fromkeys(record.values))
            records.append(record)
    if not records:
        raise DataError(f"{path.name} contains no records")
    return tuple(columns), records


def _jsonl_record(number: int, line: str) -> RawRecord:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        return RawRecord(number, {}, f"is not valid JSON ({exc.msg})")
    if not isinstance(value, dict):
        return RawRecord(number, {}, "is not a JSON object")
    return RawRecord(number, value)
