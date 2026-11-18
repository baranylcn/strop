"""The ``strop data`` command group."""

from collections import Counter
from pathlib import Path
from typing import Annotated

import typer

from strop.cli.options import DirOption, JsonOption, SkipInvalidOption, emit_json
from strop.config import StropConfig
from strop.config.enums import ColumnRole, OutputType
from strop.data import Dataset
from strop.data.models import Partition
from strop.errors import DataError
from strop.services.data import SplitOutcome, check_dataset, create_split, effective_split_config
from strop.services.project import open_project

data_app = typer.Typer(
    help="Validate the dataset and create train/validation/test splits.", no_args_is_help=True
)

MAX_LISTED_ISSUES = 20


@data_app.command("check")
def check_command(
    skip_invalid: SkipInvalidOption = False,
    as_json: JsonOption = False,
    directory: DirOption = Path(),
) -> None:
    """Validate the dataset and list invalid rows with their row numbers."""
    project = open_project(directory)
    dataset = check_dataset(project)
    if as_json:
        emit_json(_dataset_payload(project.config, dataset))
    else:
        typer.echo(_dataset_report(project.config, dataset))
    if dataset.issues and not skip_invalid:
        raise DataError(
            f"{len(dataset.issues)} invalid row(s) found; fix them or use --skip-invalid"
        )


@data_app.command("split")
def split_command(
    seed: Annotated[int | None, typer.Option(help="Random seed; defaults to strop.yaml.")] = None,
    train: Annotated[float | None, typer.Option(help="Train ratio.")] = None,
    validation: Annotated[float | None, typer.Option(help="Validation ratio.")] = None,
    test: Annotated[float | None, typer.Option(help="Test ratio; 0 disables the test set.")] = None,
    skip_invalid: SkipInvalidOption = False,
    as_json: JsonOption = False,
    directory: DirOption = Path(),
) -> None:
    """Create a reproducible train/validation/test split and store it."""
    project = open_project(directory)
    overrides = {"seed": seed, "train": train, "validation": validation, "test": test}
    outcome = create_split(
        project, effective_split_config(project, overrides), skip_invalid=skip_invalid
    )
    if as_json:
        emit_json(_split_payload(outcome))
    else:
        typer.echo(_split_report(outcome))


def _label_counts(config: StropConfig, dataset: Dataset) -> dict[str, int] | None:
    """Valid rows per expected label, largest first; None unless the task is labeled."""
    has_expected = ColumnRole.EXPECTED in config.dataset.columns.values()
    if config.output.type is not OutputType.LABEL or not has_expected:
        return None
    counts = Counter(row.expected for row in dataset.rows if row.expected is not None)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _dataset_payload(config: StropConfig, dataset: Dataset) -> dict[str, object]:
    payload: dict[str, object] = {
        "records": dataset.total_records,
        "valid_rows": len(dataset.rows),
        "columns": list(dataset.columns),
        "content_hash": dataset.content_hash,
        "issues": [{"row": i.number, "message": i.message} for i in dataset.issues],
    }
    label_counts = _label_counts(config, dataset)
    if label_counts is not None:
        payload["label_counts"] = label_counts
    return payload


def _dataset_report(config: StropConfig, dataset: Dataset) -> str:
    lines = [
        f"Dataset: {config.dataset.path.name}",
        f"Records: {dataset.total_records}, valid: {len(dataset.rows)}, "
        f"invalid: {dataset.total_records - len(dataset.rows)}",
        f"Columns: {', '.join(dataset.columns)}",
    ]
    label_counts = _label_counts(config, dataset)
    if label_counts is not None:
        lines.append("Labels: " + ", ".join(f"{label} {n}" for label, n in label_counts.items()))
    if dataset.issues:
        lines.append("Invalid rows:")
        lines.extend(f"  {issue}" for issue in dataset.issues[:MAX_LISTED_ISSUES])
        if len(dataset.issues) > MAX_LISTED_ISSUES:
            lines.append(f"  ... and {len(dataset.issues) - MAX_LISTED_ISSUES} more (see --json)")
    return "\n".join(lines)


def _split_payload(outcome: SplitOutcome) -> dict[str, object]:
    return {
        "split_id": outcome.split_id,
        "created": outcome.created,
        "seed": outcome.config.seed,
        "counts": {p.value: n for p, n in outcome.summary.counts.items()},
        "warnings": outcome.summary.warnings,
        "skipped_rows": outcome.dataset.total_records - len(outcome.dataset.rows),
    }


def _split_report(outcome: SplitOutcome) -> str:
    verb = "Created" if outcome.created else "Reused existing"
    counts = outcome.summary.counts
    lines = [
        f"{verb} split {outcome.split_id} (seed {outcome.config.seed}) "
        f"over {len(outcome.dataset.rows)} rows:",
        *(f"  {p.value:<10} {counts[p]}" for p in Partition),
    ]
    skipped = outcome.dataset.total_records - len(outcome.dataset.rows)
    if skipped:
        lines.append(f"Skipped {skipped} invalid row(s).")
    lines.extend(f"Warning: {warning}" for warning in outcome.summary.warnings)
    return "\n".join(lines)
