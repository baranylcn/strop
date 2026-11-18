import io

import pytest
from rich.console import Console
from rich.table import Table
from rich.text import Text

from strop.data.models import Partition
from strop.evaluation.models import EvaluationRecord, UsageSummary
from strop.metrics.suite import MetricReport
from strop.metrics.types import MetricValue
from strop.reporting.console import ColorMode, make_console
from strop.reporting.evaluation_view import render_evaluation
from strop.reporting.theme import delta_style, f1_style, is_fancy, status_text


def capture(mode: ColorMode) -> tuple[Console, io.StringIO]:
    console = make_console(mode)
    buffer = io.StringIO()
    console.file = buffer
    return console, buffer


def test_always_mode_colors_the_text() -> None:
    console, buffer = capture(ColorMode.ALWAYS)
    console.print(Text("ok", style="ok"))
    assert "\x1b[32m" in buffer.getvalue()


def test_never_mode_prints_plain_text() -> None:
    console, buffer = capture(ColorMode.NEVER)
    console.print(Text("ok", style="ok"))
    assert buffer.getvalue() == "ok\n"


def test_a_piped_console_is_not_fancy() -> None:
    console, _ = capture(ColorMode.NEVER)
    assert not is_fancy(console)


@pytest.mark.parametrize(
    ("value", "style"),
    [(None, "muted"), (0.95, "ok"), (0.7, "warn"), (0.2, "bad")],
)
def test_f1_style_follows_the_score(value: float | None, style: str) -> None:
    assert f1_style(value) == style


@pytest.mark.parametrize(
    ("delta", "style"), [(None, "muted"), (0.0, "muted"), (0.1, "ok"), (-0.1, "bad")]
)
def test_delta_style_marks_gains_and_losses(delta: float | None, style: str) -> None:
    assert delta_style(delta) == style


def test_status_text_keeps_the_word_and_styles_known_statuses() -> None:
    assert status_text("accepted").plain == "accepted"
    assert status_text("accepted").style == "ok"
    assert status_text("something else").style == ""


def test_evaluation_view_is_plain_without_color() -> None:
    report = MetricReport("accuracy", {"accuracy": MetricValue("accuracy", 0.5, 4)})
    record = EvaluationRecord(
        1, 1, 1, Partition.VALIDATION, "baseline", report, UsageSummary(), 4, 0, ""
    )
    console, buffer = capture(ColorMode.NEVER)
    render_evaluation(console, record, [], version_ref="v1")
    out = buffer.getvalue()
    assert "\x1b" not in out
    assert "accuracy (primary)" in out
    assert "No output problems." in out


def test_tables_render_styled_cells_with_color() -> None:
    console, buffer = capture(ColorMode.ALWAYS)
    table = Table(box=None)
    table.add_column("F1")
    table.add_row(Text("1.0000", style=f1_style(1.0)))
    console.print(table)
    assert "\x1b[32m" in buffer.getvalue()
