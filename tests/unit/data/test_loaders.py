from pathlib import Path

import pytest

from strop.config import DatasetFormat
from strop.data.loaders import file_hash, read_records
from strop.errors import DataError


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_csv_records_and_columns(tmp_path: Path) -> None:
    path = write(tmp_path / "d.csv", "a,b\n1,2\n3,4\n")
    columns, records = read_records(path, DatasetFormat.CSV)
    assert columns == ("a", "b")
    assert [r.values for r in records] == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    assert [r.number for r in records] == [1, 2]


def test_csv_handles_quoted_newlines_and_bom(tmp_path: Path) -> None:
    path = tmp_path / "d.csv"
    path.write_bytes(b'\xef\xbb\xbfa,b\n"line one\nline two",x\n')
    columns, records = read_records(path, DatasetFormat.CSV)
    assert columns == ("a", "b")
    assert records[0].values["a"] == "line one\nline two"


def test_csv_records_skip_blank_lines(tmp_path: Path) -> None:
    path = write(tmp_path / "d.csv", "a,b\n1,2\n\n3,4\n\n")
    _, records = read_records(path, DatasetFormat.CSV)
    assert [r.values for r in records] == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]
    assert [r.number for r in records] == [1, 2]
    assert all(r.error is None for r in records)


def test_csv_row_with_wrong_field_count_is_an_error_record(tmp_path: Path) -> None:
    path = write(tmp_path / "d.csv", "a,b\n1,2\n3\n")
    _, records = read_records(path, DatasetFormat.CSV)
    assert records[0].error is None
    assert records[1].error == "has 1 fields, expected 2"


@pytest.mark.parametrize(("text", "message"), [("", "no header"), ("a,a\n1,2\n", "duplicate")])
def test_csv_header_problems(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(DataError, match=message):
        read_records(write(tmp_path / "d.csv", text), DatasetFormat.CSV)


def test_jsonl_records_skip_blank_lines(tmp_path: Path) -> None:
    path = write(tmp_path / "d.jsonl", '{"a": 1}\n\n{"a": 2, "b": "x"}\n')
    columns, records = read_records(path, DatasetFormat.JSONL)
    assert columns == ("a", "b")
    assert [r.number for r in records] == [1, 3]


def test_jsonl_bad_lines_become_error_records(tmp_path: Path) -> None:
    path = write(tmp_path / "d.jsonl", '{"a": 1}\nnot json\n[1, 2]\n')
    _, records = read_records(path, DatasetFormat.JSONL)
    assert records[0].error is None
    assert "not valid JSON" in (records[1].error or "")
    assert records[2].error == "is not a JSON object"


def test_empty_jsonl_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="no records"):
        read_records(write(tmp_path / "d.jsonl", "\n\n"), DatasetFormat.JSONL)


def test_invalid_utf8_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "d.csv"
    path.write_bytes(b"a,b\n\xff\xfe,1\n")
    with pytest.raises(DataError, match="UTF-8"):
        read_records(path, DatasetFormat.CSV)


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="not found"):
        read_records(tmp_path / "absent.csv", DatasetFormat.CSV)


def test_file_hash_changes_with_content(tmp_path: Path) -> None:
    first = file_hash(write(tmp_path / "a.csv", "x\n1\n"))
    assert first == file_hash(tmp_path / "a.csv")
    assert first != file_hash(write(tmp_path / "b.csv", "x\n2\n"))
