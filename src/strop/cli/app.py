"""The Typer application and the process entry point."""

import sys
from typing import Annotated

import typer

from strop import __version__
from strop.cli.analyze import analyze_command
from strop.cli.data import data_app
from strop.cli.evaluate import baseline_command, eval_command
from strop.cli.export import clean_command, export_command
from strop.cli.final import compare_command, final_test_command
from strop.cli.init import init_command
from strop.cli.optimize import approve_command, optimize_command, reject_command
from strop.cli.prompts import prompt_app
from strop.cli.status import status_command
from strop.cli.versions import diff_command, history_command, rollback_command
from strop.errors import ExitCode, StropError
from strop.log import configure_logging

EXIT_CODES_HELP = (
    "Exit codes: 0 success, 1 failure, 2 usage or configuration error, "
    "10 paused for approval, 11 stopped by a budget, 12 interrupted."
)

app = typer.Typer(
    name="strop",
    help="Improve LLM prompts by testing them against your own data.",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_enable=False,
    epilog=EXIT_CODES_HELP,
)
app.command("init")(init_command)
app.add_typer(data_app, name="data")
app.add_typer(prompt_app, name="prompt")
app.command("diff")(diff_command)
app.command("history")(history_command)
app.command("rollback")(rollback_command)
app.command("baseline")(baseline_command)
app.command("eval")(eval_command)
app.command("status")(status_command)
app.command("analyze")(analyze_command)
app.command("optimize")(optimize_command)
app.command("approve")(approve_command)
app.command("reject")(reject_command)
app.command("test")(final_test_command)
app.command("compare")(compare_command)
app.command("export")(export_command)
app.command("clean")(clean_command)


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"strop {__version__}")
        raise typer.Exit


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_show_version, is_eager=True, help="Show the version."),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Show debug messages.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", help="Show errors only.")] = False,
) -> None:
    """Improve LLM prompts by testing them against your own data."""
    configure_logging(verbose=verbose, quiet=quiet)


def main() -> None:
    """Run the CLI and translate expected errors into exit codes."""
    try:
        app()
    except StropError as exc:
        typer.echo(f"error: {exc}", err=True)
        sys.exit(exc.exit_code)
    except KeyboardInterrupt:
        typer.echo("interrupted", err=True)
        sys.exit(ExitCode.INTERRUPTED)
