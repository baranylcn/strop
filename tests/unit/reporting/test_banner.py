import io

import pytest

from strop import __version__
from strop.reporting.banner import (
    LOGO,
    OPT_OUT_VARIABLE,
    TAGLINE,
    banner_text,
    should_show_banner,
    show_banner,
)
from strop.reporting.console import ColorMode, make_console


def test_the_logo_is_plain_ascii_and_fits_a_narrow_terminal() -> None:
    for line in LOGO:
        assert line.isascii()
        assert len(line) <= 40


def test_banner_names_the_version_and_the_tool() -> None:
    plain = banner_text().plain
    assert f"v{__version__}" in plain
    assert TAGLINE in plain


def test_banner_is_hidden_when_output_is_not_a_terminal() -> None:
    console = make_console(ColorMode.NEVER)
    buffer = io.StringIO()
    console.file = buffer
    show_banner(console)
    assert buffer.getvalue() == ""


def test_banner_is_shown_on_a_color_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(OPT_OUT_VARIABLE, raising=False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    console = make_console(ColorMode.ALWAYS)
    buffer = io.StringIO()
    console.file = buffer
    show_banner(console)
    assert TAGLINE in buffer.getvalue()


def test_the_opt_out_variable_hides_the_banner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv(OPT_OUT_VARIABLE, "1")
    assert not should_show_banner(make_console(ColorMode.ALWAYS))
