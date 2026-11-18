"""The ``optimize``, ``approve`` and ``reject`` commands."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from strop.cli.evaluate import NoCacheOption
from strop.cli.options import DirOption, JsonOption, emit_json
from strop.cli.style import echo_good, echo_narration
from strop.config.enums import ApprovalMode
from strop.config.overrides import apply_overrides
from strop.errors import ConfigError, ExitCode
from strop.reporting import ColorMode, make_console
from strop.reporting.run_view import render_run, run_payload
from strop.services.optimize import RunSummary, optimize
from strop.services.project import Project, open_project
from strop.services.review import approve, reject

Option = typer.Option


def optimize_command(
    max_turns: Annotated[int | None, Option(help="Maximum number of turns.", min=1)] = None,
    candidates: Annotated[int | None, Option(help="Candidates per turn.", min=1)] = None,
    target: Annotated[
        float | None, Option(help="Stop once the primary metric reaches this.")
    ] = None,
    patience: Annotated[
        int | None, Option(help="Stop after this many turns without gain.", min=1)
    ] = None,
    approval: Annotated[
        ApprovalMode | None, Option(help="auto, or manual to pause for approval.")
    ] = None,
    instructions: Annotated[str | None, Option(help="Extra guidance for the optimizer.")] = None,
    feedback_file: Annotated[Path | None, Option(help="Text file with extra guidance.")] = None,
    train_sample: Annotated[
        int | None, Option(help="Analyze a sample of train rows.", min=1)
    ] = None,
    max_calls: Annotated[int | None, Option(help="Model call budget for this run.", min=1)] = None,
    max_cost: Annotated[float | None, Option(help="Cost budget in USD.", min=0.0)] = None,
    max_minutes: Annotated[float | None, Option(help="Time budget in minutes.", min=0.0)] = None,
    optimizer_model: Annotated[str | None, Option(help="Use this model as the optimizer.")] = None,
    analyzer_model: Annotated[str | None, Option(help="Use this model as the analyzer.")] = None,
    resume: Annotated[bool, Option(help="Continue the unfinished run.")] = False,
    no_cache: NoCacheOption = False,
    as_json: JsonOption = False,
    directory: DirOption = Path(),
) -> None:
    """Run the optimization loop: test the prompt, revise it from the failures, and repeat."""
    project = open_project(directory).with_models(
        {"optimizer": optimizer_model, "analyzer": analyzer_model}
    )
    settings = apply_overrides(
        project.config.optimization,
        {
            "max_turns": max_turns,
            "candidates_per_turn": candidates,
            "target": target,
            "patience": patience,
            "approval": approval,
            "train_sample": train_sample,
            "instructions": _instructions(project, instructions, feedback_file),
        },
    )
    budgets = apply_overrides(
        project.config.budgets,
        {
            "max_total_model_calls": max_calls,
            "max_total_cost_usd": max_cost,
            "max_wall_time_minutes": max_minutes,
        },
    )

    def say(line: str) -> None:
        echo_narration(line, err=as_json)

    with project.database() as conn:
        try:
            summary = asyncio.run(
                optimize(
                    project,
                    conn,
                    settings,
                    budgets,
                    resume=resume,
                    use_cache=not no_cache,
                    say=say,
                )
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            typer.echo(
                "Interrupted. Progress is saved; continue with 'strop optimize --resume'.",
                err=True,
            )
            raise typer.Exit(ExitCode.INTERRUPTED) from None
    _show(summary, as_json)
    if summary.stop_reason == "awaiting_approval":
        _next_steps(summary)
        raise typer.Exit(ExitCode.PAUSED)
    if summary.stop_reason == "budget":
        typer.echo("Raise the budget and continue with 'strop optimize --resume'.", err=True)
        raise typer.Exit(ExitCode.BUDGET)


def approve_command(
    version: Annotated[str, typer.Argument(help="Pending version, such as v4.")],
    directory: DirOption = Path(),
) -> None:
    """Accept a pending candidate as the best prompt."""
    project = open_project(directory)
    with project.database() as conn:
        candidate = approve(conn, version)
    echo_good(f"v{candidate.version_number} is now the best prompt.")
    typer.echo("Continue with 'strop optimize --resume'.")


def reject_command(
    version: Annotated[str, typer.Argument(help="Pending version, such as v4.")],
    reason: Annotated[str, Option(help="Why it is rejected.")] = "",
    directory: DirOption = Path(),
) -> None:
    """Discard a pending candidate. The best prompt stays unchanged."""
    project = open_project(directory)
    with project.database() as conn:
        candidate = reject(conn, version, reason)
    typer.echo(f"v{candidate.version_number} was rejected; the best prompt is unchanged.")
    typer.echo("Continue with 'strop optimize --resume'.")


def _instructions(project: Project, text: str | None, file: Path | None) -> str | None:
    parts = [project.config.optimization.instructions, text or ""]
    if file is not None:
        try:
            parts.append(file.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(f"cannot read the feedback file {file}: {exc.strerror}") from exc
    joined = "\n".join(part.strip() for part in parts if part.strip())
    return joined or None


def _show(summary: RunSummary, as_json: bool) -> None:
    if as_json:
        emit_json(run_payload(summary))
        return
    render_run(make_console(ColorMode.AUTO), summary)


def _next_steps(summary: RunSummary) -> None:
    pending = summary.pending
    if pending is None or pending.version_number is None:
        return
    ref = f"v{pending.version_number}"
    typer.echo(f"Review it with 'strop diff {ref}', then:", err=True)
    typer.echo(f"  strop approve {ref}   or   strop reject {ref}", err=True)
    typer.echo("  strop optimize --resume", err=True)
