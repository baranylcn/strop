"""Terminal rendering and JSON payloads for optimization runs."""

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from strop.formatting import fmt, shorten
from strop.prompts.diff import diff_templates
from strop.reporting.diff_view import render_diff
from strop.reporting.theme import delta_style, status_text
from strop.services.optimize import RunSummary
from strop.storage.runs import CandidateRecord

_STOP_TEXT = {
    "max_turns": "reached the maximum number of turns",
    "target_reached": "reached the target metric",
    "patience": "no accepted improvement for the configured number of turns",
    "no_failures": "no failures left on the training examples",
    "budget": "stopped by a budget",
    "awaiting_approval": "paused for approval",
}


def stop_text(summary: RunSummary) -> str:
    text = _STOP_TEXT.get(summary.stop_reason, summary.stop_reason)
    if summary.stop_detail:
        text += f" ({summary.stop_detail})"
    if summary.pending is not None:
        text += (
            f": v{summary.pending.version_number} is waiting for 'strop approve' or 'strop reject'"
        )
    return text


def render_run(console: Console, summary: RunSummary) -> None:
    """Print the run result: why it stopped, the metric change, candidates, and the prompt diff."""
    paused = summary.pending is not None
    console.print(
        Text(f"Run {summary.run.id}: {stop_text(summary)}.", style="warn" if paused else "title"),
        soft_wrap=True,
    )
    console.print(_change_line(summary), soft_wrap=True)
    if summary.candidates:
        console.print(_candidate_table(summary.candidates))
    cost = "unavailable" if summary.cost_usd is None else f"${summary.cost_usd:.4f}"
    console.print(Text(f"Model calls: {summary.calls} | Cost: {cost}", style="dim"), soft_wrap=True)
    for warning in summary.warnings:
        console.print(Text(f"Warning: {warning}", style="warn"), soft_wrap=True)
    _render_final_diff(console, summary)


def _render_final_diff(console: Console, summary: RunSummary) -> None:
    if summary.pending is not None:
        return
    if summary.final.number == summary.initial.number:
        message = Text("No improvement was accepted; the best prompt is unchanged.", style="warn")
        console.print(message, soft_wrap=True)
        return
    diff = diff_templates(summary.initial.template, summary.final.template)
    console.print(
        Text(f"Prompt changes, {summary.initial.ref} -> {summary.final.ref}:", style="title"),
        soft_wrap=True,
    )
    render_diff(diff, console)


def _change_line(summary: RunSummary) -> Text:
    primary = _primary(summary)
    before, after = _value(summary.baseline), _value(summary.result)
    line = Text(f"{summary.start.ref} {primary} {fmt(before)}  ->  ")
    line.append(f"{summary.final.ref} {primary} {fmt(after)}", style=_outcome_style(before, after))
    line.append(" (validation)")
    return line


def _outcome_style(before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return "title"
    return delta_style(after - before) if after != before else "title"


def _candidate_table(candidates: list[CandidateRecord]) -> Table:
    table = Table(box=None, pad_edge=False, header_style="label")
    for column in ("Turn", "Version", "Result", "Change", "Summary"):
        table.add_column(column)
    for item in candidates:
        delta = Text("-", style="muted")
        if item.primary_delta is not None:
            delta = Text(f"{item.primary_delta:+.4f}", style=delta_style(item.primary_delta))
        version = f"v{item.version_number}" if item.version_number else "-"
        explained = item.status in {"invalid", "rejected"}
        note = (item.reason or item.change_summary) if explained else item.change_summary
        table.add_row(str(item.turn), version, status_text(item.status), delta, shorten(note, 60))
    return table


def _primary(summary: RunSummary) -> str:
    record = summary.result or summary.baseline
    return record.report.primary if record else "primary metric"


def _value(record: Any) -> float | None:
    return record.report.primary_value.value if record is not None else None


def run_payload(summary: RunSummary) -> dict[str, Any]:
    return {
        "run": summary.run.id,
        "status": summary.run.status,
        "stop_reason": summary.stop_reason,
        "stop_detail": summary.stop_detail,
        "initial_version": summary.initial.number,
        "start_version": summary.start.number,
        "best_version": summary.final.number,
        "primary_metric": _primary(summary),
        "start_value": _value(summary.baseline),
        "best_value": _value(summary.result),
        "turns": len([t for t in summary.turns if t.status == "done"]),
        "pending_version": summary.pending.version_number if summary.pending else None,
        "model_calls": summary.calls,
        "cost_usd": summary.cost_usd,
        "candidates": [
            {
                "turn": c.turn,
                "version": c.version_number,
                "status": c.status,
                "primary_delta": c.primary_delta,
                "summary": c.change_summary,
                "reason": c.reason,
            }
            for c in summary.candidates
        ],
        "diff": diff_templates(summary.initial.template, summary.final.template).to_payload(),
    }
