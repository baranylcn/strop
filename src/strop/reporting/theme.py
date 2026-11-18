"""Colors and small styling helpers shared by every terminal view.

Color only appears on a real terminal. Pipes, files, ``NO_COLOR`` and ``--color never`` get the
same text without any styling, so output stays readable and testable.
"""

from rich.console import Console
from rich.text import Text
from rich.theme import Theme

THEME = Theme(
    {
        "ok": "green",
        "warn": "yellow",
        "bad": "bold red",
        "info": "cyan",
        "muted": "dim",
        "label": "bold cyan",
        "title": "bold",
    }
)

STATUS_STYLES = {
    "accepted": "ok",
    "rejected": "bad",
    "pending": "warn",
    "invalid": "muted",
    "evaluated": "info",
}


def is_fancy(console: Console) -> bool:
    """True when the console shows colors and boxes: a real terminal with color enabled."""
    return console.is_terminal and not console.no_color and console.color_system is not None


def f1_style(value: float | None) -> str:
    """Style for an F1 score: higher is better."""
    if value is None:
        return "muted"
    if value >= 0.9:
        return "ok"
    return "warn" if value >= 0.6 else "bad"


def delta_style(delta: float | None) -> str:
    """Style for a change that is already signed so that positive means better."""
    if delta is None or delta == 0:
        return "muted"
    return "ok" if delta > 0 else "bad"


def status_text(status: str) -> Text:
    return Text(status, style=STATUS_STYLES.get(status, ""))
