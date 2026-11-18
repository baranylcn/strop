"""Color for the plain lines the CLI prints with ``typer.echo``.

Styling is applied only when the target stream is a terminal and ``NO_COLOR`` is not set, so
piped output and ``--json`` stay free of escape codes.
"""

import os
import sys
from typing import IO

import click
import typer

_ERROR = {"fg": "red", "bold": True}
_NOTE = {"fg": "cyan"}
_GOOD = {"fg": "green"}
_WARN = {"fg": "yellow"}


def _colors_enabled(stream: IO[str]) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ


def paint(text: str, *, err: bool = False, **style: object) -> str:
    """``text`` with the given click style, or unchanged when color is off."""
    stream = sys.stderr if err else sys.stdout
    return click.style(text, **style) if _colors_enabled(stream) else text  # type: ignore[arg-type]


def echo_error(message: str) -> None:
    typer.echo(paint("error:", err=True, **_ERROR) + f" {message}", err=True)


def echo_note(message: str, *, err: bool = False) -> None:
    """A line that starts with ``Note:``; the label is colored."""
    typer.echo(paint("Note:", err=err, **_NOTE) + f" {message}", err=err)


def echo_good(message: str, *, err: bool = False) -> None:
    typer.echo(paint(message, err=err, **_GOOD), err=err)


def echo_warn(message: str, *, err: bool = False) -> None:
    typer.echo(paint(message, err=err, **_WARN), err=err)


def echo_narration(line: str, *, err: bool = False) -> None:
    """One progress line from the optimize loop, colored by what it reports."""
    stripped = line.lstrip()
    if stripped.startswith("Turn "):
        typer.echo(paint(line, err=err, bold=True, fg="cyan"), err=err)
    elif stripped.startswith("Accepted "):
        echo_good(line, err=err)
    elif "discarded" in stripped or stripped.startswith("No candidate"):
        echo_warn(line, err=err)
    else:
        typer.echo(line, err=err)
