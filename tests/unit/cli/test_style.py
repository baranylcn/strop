import pytest

from strop.cli import style
from strop.cli.progress import render_bar


class Tty:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def test_paint_is_plain_when_piped(capsys: pytest.CaptureFixture[str]) -> None:
    style.echo_error("boom")
    assert capsys.readouterr().err == "error: boom\n"


def test_paint_colors_on_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdout", Tty(True))
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert style.paint("hi", fg="green") == "\x1b[32mhi\x1b[0m"


def test_no_color_disables_painting_on_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdout", Tty(True))
    monkeypatch.setenv("NO_COLOR", "1")
    assert style.paint("hi", fg="green") == "hi"


@pytest.mark.parametrize(
    "line",
    ["Turn 1: v1 scores macro_f1 0.5000.", "  Accepted v2 as the new best prompt.", "plain line"],
)
def test_narration_text_is_never_changed(line: str, capsys: pytest.CaptureFixture[str]) -> None:
    style.echo_narration(line)
    assert capsys.readouterr().out == line + "\n"


def test_note_keeps_its_label(capsys: pytest.CaptureFixture[str]) -> None:
    style.echo_note("keep .env private")
    assert capsys.readouterr().out == "Note: keep .env private\n"


def test_progress_bar_fills_with_the_done_share() -> None:
    bar = render_bar("Baseline", 6, 12)
    assert bar.plain.count("━") == 12
    assert bar.plain.endswith("6/12")


def test_progress_bar_handles_an_empty_total() -> None:
    assert render_bar("x", 0, 0).plain.count("━") == 24
