"""Terminal rendering and JSON payloads for evaluations."""

from collections import Counter
from collections.abc import Sequence
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from strop.evaluation.models import EvaluationRecord, ExampleOutcome, UsageSummary
from strop.formatting import fmt, shorten
from strop.reporting.theme import f1_style


def render_evaluation(
    console: Console,
    record: EvaluationRecord,
    outcomes: Sequence[ExampleOutcome],
    *,
    version_ref: str,
    show_errors: int = 5,
) -> None:
    """Print the metrics, error summary, per-class scores, usage, and sample failures."""
    title = (
        f"Evaluation {record.id}: {version_ref} on {record.partition.value} "
        f"({record.sample_count} examples, {record.kind})"
    )
    console.print(Text(title, style="title"), soft_wrap=True)
    console.print(_metrics_table(record))
    console.print(_error_summary(outcomes), soft_wrap=True)
    classes = _per_class_table(record)
    if classes is not None:
        console.print(classes)
    console.print(Text(usage_line(record.usage), style="dim"), soft_wrap=True)
    for index, line in enumerate(failure_lines(outcomes, show_errors)):
        style = "warn" if index == 0 else ("bad" if "provider_error" in line else "")
        console.print(Text(line, style=style), soft_wrap=True)


def _metrics_table(record: EvaluationRecord) -> Table:
    table = Table(box=None, pad_edge=False, header_style="label")
    for column in ("Metric", "Value", "Samples", "Note"):
        table.add_column(column)
    for name, metric in record.report.values.items():
        primary = name == record.report.primary
        label = Text(f"{name} (primary)" if primary else name, style="info" if primary else "")
        value = Text(fmt(metric.value), style=_value_style(name, metric.value, primary))
        note = Text("subjective, LLM-judged" if metric.subjective else "", style="warn")
        table.add_row(label, value, str(metric.samples), note)
    return table


def _value_style(name: str, value: float | None, primary: bool) -> str:
    """Only a short valid output rate is flagged; other values are shown without a verdict."""
    if name == "valid_output_rate" and value is not None and value < 1.0:
        return "warn"
    return "title" if primary else ""


def _error_summary(outcomes: Sequence[ExampleOutcome]) -> Text:
    codes = Counter(o.error for o in outcomes if o.error)
    wrong = sum(1 for o in outcomes if _is_wrong(o))
    parts = [f"{code} {count}" for code, count in sorted(codes.items())]
    if wrong:
        parts.append(f"valid but wrong {wrong}")
    if not parts:
        return Text("No output problems.", style="ok")
    return Text(f"Output problems: {', '.join(parts)}", style="bad")


def _is_wrong(outcome: ExampleOutcome) -> bool:
    return (
        outcome.value is not None
        and outcome.expected is not None
        and outcome.value != outcome.expected
    )


def _per_class_table(record: EvaluationRecord) -> Table | None:
    per_class = record.report.primary_value.details.get("per_class")
    if not per_class:
        return None
    table = Table(
        box=None, pad_edge=False, header_style="label", title="Per class", title_justify="left"
    )
    for column in ("Class", "Precision", "Recall", "F1", "Support"):
        table.add_column(column)
    for label, scores in per_class.items():
        table.add_row(
            label,
            fmt(scores["precision"]),
            fmt(scores["recall"]),
            Text(fmt(scores["f1"]), style=f1_style(scores["f1"])),
            str(scores["support"]),
        )
    return table


def usage_line(usage: UsageSummary) -> str:
    cost = "unavailable" if usage.cost_usd is None else f"${usage.cost_usd:.4f}"
    if usage.cost_usd is not None and not usage.cost_complete:
        cost += " (partial)"
    tokens = "unavailable" if usage.total_tokens is None else f"{usage.total_tokens:,}"
    latency = "unavailable" if usage.mean_latency_s is None else f"{usage.mean_latency_s:.2f}s"
    return (
        f"Calls: {usage.calls} ({usage.cached_calls} cached) | Tokens: {tokens} | "
        f"Cost: {cost} | Mean latency: {latency}"
    )


def failure_lines(outcomes: Sequence[ExampleOutcome], limit: int) -> list[str]:
    """One line per failing example, up to ``limit``, with a trailer for the rest."""
    failing = [o for o in outcomes if o.error or _is_wrong(o)]
    if limit <= 0 or not failing:
        return []
    lines = ["Examples that failed:"]
    for outcome in failing[:limit]:
        if outcome.error:
            got = shorten(outcome.detail or outcome.raw_output)
            lines.append(f"  {outcome.row_id}: {outcome.error} ({got})")
        else:
            lines.append(
                f"  {outcome.row_id}: expected {shorten(outcome.expected or '')!r}, "
                f"got {shorten(outcome.value or '')!r}"
            )
    if len(failing) > limit:
        lines.append(f"  ... and {len(failing) - limit} more")
    return lines


def record_payload(record: EvaluationRecord, version_ref: str) -> dict[str, Any]:
    usage = record.usage
    return {
        "evaluation": record.id,
        "version": version_ref,
        "partition": record.partition.value,
        "kind": record.kind,
        "samples": record.sample_count,
        "errors": record.error_count,
        "primary_metric": record.report.primary,
        "metrics": {
            name: {"value": m.value, "samples": m.samples, "subjective": m.subjective}
            for name, m in record.report.values.items()
        },
        "usage": {
            "calls": usage.calls,
            "cached_calls": usage.cached_calls,
            "total_tokens": usage.total_tokens,
            "cost_usd": usage.cost_usd,
            "cost_complete": usage.cost_complete,
            "mean_latency_s": usage.mean_latency_s,
        },
    }
