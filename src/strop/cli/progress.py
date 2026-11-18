"""A progress bar on stderr, shown only on an interactive terminal."""

import sys

from rich.text import Text

from strop.evaluation.runner import Progress
from strop.reporting.console import ColorMode, make_console

_WIDTH = 24


def render_bar(label: str, done: int, total: int) -> Text:
    """``label  ━━━━────  done/total`` with the finished part highlighted."""
    filled = _WIDTH if total <= 0 else min(_WIDTH, round(_WIDTH * done / total))
    line = Text(f"{label}  ")
    line.append("━" * filled, style="info")
    line.append("─" * (_WIDTH - filled), style="muted")
    line.append(f"  {done}/{total}")
    return line


def stderr_progress(label: str) -> Progress | None:
    """Return a callback that redraws the bar on stderr, or None when stderr is piped."""
    if not sys.stderr.isatty():
        return None
    console = make_console(ColorMode.AUTO, stderr=True)

    def update(done: int, total: int) -> None:
        finished = done >= total
        console.print(render_bar(label, done, total), end="\n" if finished else "\r")

    return update
