"""The STROP logo shown when the tool is started by hand."""

import os
import sys

from rich.console import Console
from rich.text import Text

from strop import __version__
from strop.reporting.theme import is_fancy

LOGO = (
    r"  ____ _____ ____   ___  ____  ",
    r" / ___|_   _|  _ \ / _ \|  _ \ ",
    r" \___ \ | | | |_) | | | | |_) |",
    r"  ___) || | |  _ <| |_| |  __/ ",
    r" |____/ |_| |_| \_\\___/|_|    ",
)
TAGLINE = "Improve LLM prompts by testing them against your own data."
_GRADIENT = ("cyan", "cyan", "bright_cyan", "bright_blue", "blue")
OPT_OUT_VARIABLE = "STROP_NO_BANNER"


def banner_text() -> Text:
    """The logo with a vertical color gradient, the version, and the tagline."""
    text = Text()
    for line, color in zip(LOGO, _GRADIENT, strict=True):
        text.append(line + "\n", style=f"bold {color}")
    text.append(f"  v{__version__}  ", style="muted")
    text.append(TAGLINE + "\n", style="muted")
    return text


def should_show_banner(console: Console) -> bool:
    """Only on a real terminal with color, and never when the user opted out."""
    return is_fancy(console) and OPT_OUT_VARIABLE not in os.environ


def show_banner(console: Console) -> None:
    if should_show_banner(console):
        console.print(banner_text())


def started_without_arguments() -> bool:
    return len(sys.argv) == 1
