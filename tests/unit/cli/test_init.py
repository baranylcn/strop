from pathlib import Path

import pytest

from strop import __version__
from strop.config import load_config
from strop.storage import ProjectPaths, connect
from tests.helpers import CliRunner


def test_version_flag(run_cli: CliRunner) -> None:
    code, out, _ = run_cli("--version")
    assert code == 0
    assert out.strip() == f"strop {__version__}"


def test_help_lists_the_shell_completion_options(run_cli: CliRunner) -> None:
    code, out, _ = run_cli("--help")
    assert code == 0
    assert "--install-completion" in out
    assert "--show-completion" in out


def test_no_arguments_shows_help(run_cli: CliRunner) -> None:
    _, out, err = run_cli()
    assert "init" in out + err


def test_init_creates_project_files(
    run_cli: CliRunner, init_args: list[str], project_dir: Path
) -> None:
    code, out, _ = run_cli(*init_args)
    assert code == 0
    assert "Created strop.yaml" in out
    assert (project_dir / "prompt.yaml").is_file()
    assert (project_dir / ".strop" / "strop.db").is_file()
    config = load_config(project_dir / "strop.yaml")
    assert config.project.name == "demo"
    assert config.dataset.expected_column == "category"
    assert config.models.optimizer is not None


def test_init_discloses_data_recipients(run_cli: CliRunner, init_args: list[str]) -> None:
    _, out, _ = run_cli(*init_args)
    assert "dataset rows will be sent to: anthropic, openai" in out


def test_init_records_project_metadata(
    run_cli: CliRunner, init_args: list[str], project_dir: Path
) -> None:
    run_cli(*init_args)
    conn = connect(ProjectPaths(project_dir).database)
    rows = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    assert rows["project_name"] == "demo"
    assert rows["strop_version"] == __version__


def test_init_keeps_an_existing_prompt_file(
    run_cli: CliRunner, init_args: list[str], project_dir: Path
) -> None:
    prompt = project_dir / "prompt.yaml"
    prompt.write_text("existing", encoding="utf-8")
    run_cli(*init_args)
    assert prompt.read_text(encoding="utf-8") == "existing"


def test_init_refuses_to_overwrite_config_without_force(
    run_cli: CliRunner, init_args: list[str]
) -> None:
    assert run_cli(*init_args)[0] == 0
    code, _, err = run_cli(*init_args)
    assert code == 2
    assert "--force" in err
    assert run_cli(*init_args, "--force")[0] == 0


def test_init_reports_a_missing_flag_without_prompting(run_cli: CliRunner) -> None:
    code, _, err = run_cli("init", "--name", "demo")
    assert code == 2
    assert "--task" in err


def test_init_requires_the_dataset_file(run_cli: CliRunner, init_args: list[str]) -> None:
    init_args[init_args.index("data.csv")] = "absent.csv"
    code, _, err = run_cli(*init_args)
    assert code == 2
    assert "dataset file not found" in err


@pytest.mark.parametrize(
    ("flag", "value", "message"),
    [
        ("--labels", "only-one", "at least two labels"),
        ("--constraint", "recall", "invalid constraint"),
        ("--input", "category", "more than one role"),
    ],
)
def test_init_rejects_invalid_values(
    run_cli: CliRunner, init_args: list[str], flag: str, value: str, message: str
) -> None:
    code, _, err = run_cli(*init_args, flag, value)
    assert code == 2
    assert message in err
