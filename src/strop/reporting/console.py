"""Console construction with an explicit color mode."""

from enum import StrEnum

from rich.console import Console

from strop.reporting.theme import THEME


class ColorMode(StrEnum):
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


def make_console(mode: ColorMode = ColorMode.AUTO, *, stderr: bool = False) -> Console:
    """A console for stdout or stderr; ``auto`` colors only on a terminal and honors NO_COLOR."""
    if mode is ColorMode.ALWAYS:
        return Console(
            theme=THEME,
            highlight=False,
            stderr=stderr,
            force_terminal=True,
            color_system="standard",
        )
    if mode is ColorMode.NEVER:
        return Console(
            theme=THEME,
            highlight=False,
            stderr=stderr,
            force_terminal=False,
            no_color=True,
            color_system=None,
        )
    return Console(theme=THEME, highlight=False, stderr=stderr)
