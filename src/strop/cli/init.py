"""The ``strop init`` command."""

from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from strop.cli.options import DirOption
from strop.cli.style import echo_good, echo_note
from strop.config import DatasetFormat, OutputType, StropConfig
from strop.config.constraints import parse_constraints
from strop.config.io import format_errors
from strop.config.rules import load_rubrics, parse_rules
from strop.errors import ConfigError
from strop.services.scaffold import data_recipients, scaffold_project

Option = typer.Option


def init_command(
    name: Annotated[str, Option(help="Project name.")],
    task: Annotated[str, Option(help="One-sentence description of what the prompt must do.")],
    data: Annotated[Path, Option(help="Dataset file (CSV or JSONL), relative to the project.")],
    input_columns: Annotated[
        list[str], Option("--input", help="Dataset column used as a prompt variable. Repeatable.")
    ],
    output_type: Annotated[OutputType, Option(help="Kind of output the model must produce.")],
    metric: Annotated[str, Option(help="Primary metric, for example macro_f1.")],
    target_model: Annotated[str, Option(help="Model the prompt is optimized for (LiteLLM name).")],
    expected: Annotated[
        str | None, Option(help="Dataset column holding the expected output.")
    ] = None,
    metadata: Annotated[
        list[str] | None, Option(help="Dataset column kept as metadata. Repeatable.")
    ] = None,
    labels: Annotated[str, Option(help="Comma-separated labels, for output type 'label'.")] = "",
    output_schema: Annotated[
        Path | None, Option(help="JSON schema file the output must satisfy, for type 'json'.")
    ] = None,
    secondary_metric: Annotated[
        list[str] | None, Option(help="Additional metric to report. Repeatable.")
    ] = None,
    constraint: Annotated[
        list[str] | None, Option(help="Metric limit such as 'valid_output_rate>=0.98'. Repeatable.")
    ] = None,
    rule: Annotated[
        list[str] | None, Option(help="Output check such as 'short=max_words:120'. Repeatable.")
    ] = None,
    metric_file: Annotated[
        Path | None, Option(help="Python file defining score(output, row); metric name 'custom'.")
    ] = None,
    rubric_file: Annotated[
        Path | None, Option(help="YAML file of judge rubrics; each becomes metric 'judge:<name>'.")
    ] = None,
    optimizer_model: Annotated[str | None, Option(help="Model that proposes revisions.")] = None,
    analyzer_model: Annotated[str | None, Option(help="Model that summarizes failures.")] = None,
    judge_model: Annotated[str | None, Option(help="Model that scores rubric metrics.")] = None,
    prompt: Annotated[Path, Option(help="Prompt file to create or use.")] = Path("prompt.yaml"),
    data_format: Annotated[
        DatasetFormat | None, Option("--format", help="Dataset format; inferred if omitted.")
    ] = None,
    id_column: Annotated[str | None, Option(help="Dataset column with a unique row id.")] = None,
    seed: Annotated[int, Option(help="Random seed for data splits.")] = 42,
    directory: DirOption = Path(),
    force: Annotated[bool, Option(help="Overwrite an existing strop.yaml.")] = False,
) -> None:
    """Create strop.yaml, a starter prompt, and the local .strop/ state directory."""
    raw = {
        "project": {"name": name, "task_description": task},
        "prompt": {"file": str(prompt)},
        "dataset": {
            "path": str(data),
            "format": data_format,
            "id_column": id_column,
            "columns": _column_roles(input_columns, expected, metadata or []),
        },
        "output": {
            "type": output_type,
            "labels": [item.strip() for item in labels.split(",") if item.strip()],
            "schema_file": str(output_schema) if output_schema else None,
        },
        "models": _models(target_model, optimizer_model, analyzer_model, judge_model),
        "metrics": {
            "primary": metric,
            "secondary": secondary_metric or [],
            "constraints": {
                k: v.model_dump() for k, v in parse_constraints(constraint or []).items()
            },
            "rules": {k: v.model_dump(mode="json") for k, v in parse_rules(rule or []).items()},
            "python": {"file": str(metric_file)} if metric_file else None,
            "judges": _rubrics(directory, rubric_file),
        },
        "split": {"seed": seed},
    }
    config = _validate(raw)
    for entry in scaffold_project(config, directory, force=force):
        echo_good(f"Created {entry}")
    echo_note(f"dataset rows will be sent to: {', '.join(data_recipients(config))}")
    echo_note("keep .strop/ and .env out of version control; they hold outputs and keys.")


def _column_roles(inputs: list[str], expected: str | None, metadata: list[str]) -> dict[str, str]:
    roles: dict[str, str] = {}
    pairs = [(c, "input") for c in inputs] + [(c, "metadata") for c in metadata]
    if expected:
        pairs.append((expected, "expected"))
    for column, role in pairs:
        if column in roles:
            raise ConfigError(f"column '{column}' is given more than one role")
        roles[column] = role
    return roles


def _models(
    target: str, optimizer: str | None, analyzer: str | None, judge: str | None
) -> dict[str, Any]:
    chosen = {"target": target, "optimizer": optimizer, "analyzer": analyzer, "judge": judge}
    return {role: {"model": model} for role, model in chosen.items() if model}


def _validate(raw: dict[str, Any]) -> StropConfig:
    try:
        return StropConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid options:\n{format_errors(exc)}") from exc


def _rubrics(directory: Path, file: Path | None) -> dict[str, Any]:
    if file is None:
        return {}
    return {name: spec.model_dump() for name, spec in load_rubrics(directory / file).items()}
