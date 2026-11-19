"""Writing the exported prompt and report files."""

import csv
import io
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from strop.data.models import Partition
from strop.errors import ConfigError
from strop.prompts.versions import PromptVersion
from strop.reporting.prompt_export import PromptFormat, render_prompt
from strop.reporting.report_markdown import render_markdown
from strop.services.project import Project
from strop.services.prompts import ensure_initial_version, resolve_version
from strop.services.report import build_report
from strop.storage.evaluations import EvaluationRepository
from strop.storage.prompts import PromptRepository

CSV_COLUMNS = (
    "evaluation_id", "partition", "row_id", "expected", "model_output", "normalized_output",
    "error", "primary_score", "feedback", "latency_s", "total_tokens", "cost_usd",
)  # fmt: skip


@dataclass(frozen=True)
class ExportResult:
    version: PromptVersion
    files: list[Path]


def export_project(  # noqa: PLR0913
    project: Project,
    conn: sqlite3.Connection,
    *,
    ref: str | None,
    out: Path,
    prompt_format: PromptFormat,
    include_results: bool,
    write_prompt: Path | None,
    force: bool,
    keep_markers: bool = False,
) -> ExportResult:
    """Write the selected prompt, a JSON and Markdown report, and per-example results."""
    prompts = PromptRepository(conn)
    ensure_initial_version(project, prompts)
    version = resolve_version(prompts, ref)
    report = build_report(project, conn, version)
    targets = {
        out / f"prompt_{version.ref}.{prompt_format.value}": render_prompt(
            version, prompt_format, keep_markers=keep_markers
        ),
        out / "report.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        out / "report.md": render_markdown(report),
    }
    if include_results:
        targets[out / "results.csv"] = _results_csv(conn, version, report)
    if write_prompt is not None:
        targets[write_prompt] = render_prompt(version, PromptFormat.YAML, keep_markers=keep_markers)
    _check_overwrite(list(targets), force)
    for path, text in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
    return ExportResult(version, list(targets))


def _check_overwrite(paths: list[Path], force: bool) -> None:
    existing = [p for p in paths if p.exists()]
    if existing and not force:
        names = ", ".join(str(p) for p in existing)
        raise ConfigError(f"would overwrite {names}; pass --force to replace the files")


def _results_csv(conn: sqlite3.Connection, version: PromptVersion, report: dict[str, Any]) -> str:
    evals = EvaluationRepository(conn)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    primary = str(report["metrics"]["primary"])
    for partition in (Partition.VALIDATION, Partition.TEST):
        found = evals.find(prompt_number=version.number, partition=partition, limit=1)
        for record in found:
            for o in evals.outcomes(record.id):
                writer.writerow(
                    [
                        record.id, partition.value, o.row_id, o.expected, o.raw_output, o.value,
                        o.error, o.scores.get(primary), o.feedback, o.latency_s, o.total_tokens,
                        o.cost_usd,
                    ]
                )  # fmt: skip
    return buffer.getvalue()
