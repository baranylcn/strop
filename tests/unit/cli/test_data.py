import json
from pathlib import Path

from strop.config import load_config
from strop.services.data import effective_split_config
from strop.services.project import open_project
from tests.helpers import CliRunner, write_dataset


def test_check_reports_a_clean_dataset(run_cli: CliRunner, project: Path) -> None:
    code, out, _ = run_cli("data", "check", "--dir", str(project))
    assert code == 0
    assert "Records: 100, valid: 100, invalid: 0" in out


def test_check_lists_invalid_rows_and_fails(run_cli: CliRunner, project: Path) -> None:
    write_dataset(project, bad_row=True)
    code, out, err = run_cli("data", "check", "--dir", str(project))
    assert code == 2
    assert "row 2: input column 'message' is empty" in out
    assert "1 invalid row(s) found" in err


def test_check_with_skip_invalid_succeeds(run_cli: CliRunner, project: Path) -> None:
    write_dataset(project, bad_row=True)
    code, _, _ = run_cli("data", "check", "--dir", str(project), "--skip-invalid")
    assert code == 0


def test_check_json_output(run_cli: CliRunner, project: Path) -> None:
    write_dataset(project, bad_row=True)
    _, out, _ = run_cli("data", "check", "--dir", str(project), "--skip-invalid", "--json")
    payload = json.loads(out)
    assert payload["valid_rows"] == 99
    assert payload["issues"] == [{"row": 2, "message": "input column 'message' is empty"}]


def test_check_shows_the_label_counts_largest_first(run_cli: CliRunner, project: Path) -> None:
    lines = ["message,category"] + [f"m{i},{'refund' if i < 70 else 'billing'}" for i in range(100)]
    (project / "data.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    _, out, _ = run_cli("data", "check", "--dir", str(project))
    assert "Labels: refund 70, billing 30" in out


def test_check_orders_equal_label_counts_by_name(run_cli: CliRunner, project: Path) -> None:
    _, out, _ = run_cli("data", "check", "--dir", str(project))
    assert "Labels: billing 50, refund 50" in out


def test_check_counts_only_valid_rows(run_cli: CliRunner, project: Path) -> None:
    write_dataset(project, bad_row=True)
    _, out, _ = run_cli("data", "check", "--dir", str(project), "--skip-invalid")
    assert "Labels: billing 50, refund 49" in out


def test_check_json_has_label_counts(run_cli: CliRunner, project: Path) -> None:
    _, out, _ = run_cli("data", "check", "--dir", str(project), "--json")
    payload = json.loads(out)
    assert payload["label_counts"] == {"billing": 50, "refund": 50}
    assert list(payload["label_counts"]) == ["billing", "refund"]


def test_check_has_no_label_counts_without_an_expected_column(
    run_cli: CliRunner, project: Path
) -> None:
    config = project / "strop.yaml"
    config.write_text(
        config.read_text(encoding="utf-8").replace("category: expected", "category: ignore"),
        encoding="utf-8",
    )
    _, out, _ = run_cli("data", "check", "--dir", str(project))
    assert "Labels:" not in out
    _, out, _ = run_cli("data", "check", "--dir", str(project), "--json")
    assert "label_counts" not in json.loads(out)


def test_split_creates_then_reuses(run_cli: CliRunner, project: Path) -> None:
    args = ("data", "split", "--dir", str(project))
    code, out, _ = run_cli(*args)
    assert code == 0
    assert "Created split 1 (seed 42) over 100 rows" in out
    assert "train" in out
    assert "60" in out
    _, again, _ = run_cli(*args)
    assert "Reused existing split 1" in again


def test_split_with_a_new_seed_creates_another_split(run_cli: CliRunner, project: Path) -> None:
    run_cli("data", "split", "--dir", str(project))
    _, out, _ = run_cli("data", "split", "--dir", str(project), "--seed", "7")
    assert "Created split 2 (seed 7)" in out


def test_split_json_output_and_overrides(run_cli: CliRunner, project: Path) -> None:
    _, out, _ = run_cli(
        "data", "split", "--dir", str(project), "--train", "0.8", "--test", "0", "--json"
    )
    payload = json.loads(out)
    assert payload["counts"] == {"train": 80, "validation": 20, "test": 0}
    assert any("no test partition" in w for w in payload["warnings"])


def test_split_refuses_invalid_rows_unless_skipped(run_cli: CliRunner, project: Path) -> None:
    write_dataset(project, bad_row=True)
    code, _, err = run_cli("data", "split", "--dir", str(project))
    assert code == 2
    assert "--skip-invalid" in err
    code, out, _ = run_cli("data", "split", "--dir", str(project), "--skip-invalid")
    assert code == 0
    assert "Skipped 1 invalid row(s)." in out


def test_data_commands_need_a_project(run_cli: CliRunner, tmp_path: Path) -> None:
    code, _, err = run_cli("data", "check", "--dir", str(tmp_path))
    assert code == 2
    assert "strop init" in err


def test_effective_split_config_applies_only_given_overrides(
    run_cli: CliRunner, project: Path
) -> None:
    opened = open_project(project)
    config = effective_split_config(opened, {"seed": 5, "train": None})
    assert config.seed == 5
    assert config.train == load_config(project / "strop.yaml").split.train
