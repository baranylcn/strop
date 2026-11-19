"""The ``export`` and ``clean`` commands."""

from pathlib import Path
from typing import Annotated

import typer

from strop.cli.options import DirOption, JsonOption, emit_json
from strop.reporting.prompt_export import PromptFormat
from strop.services.clean import clean_project
from strop.services.export import export_project
from strop.services.project import open_project


def export_command(
    version: Annotated[
        str | None, typer.Argument(help="Version such as v2; default: best.")
    ] = None,
    out: Annotated[Path, typer.Option(help="Output directory, relative to the project.")] = Path(
        "exports"
    ),
    prompt_format: Annotated[
        PromptFormat, typer.Option(help="Format of the exported prompt file.")
    ] = PromptFormat.MD,
    results: Annotated[
        bool, typer.Option(help="Also write results.csv with per-example model outputs.")
    ] = True,
    write_prompt: Annotated[
        Path | None, typer.Option(help="Also write the prompt as a Strop prompt YAML file here.")
    ] = None,
    keep_markers: Annotated[
        bool,
        typer.Option(help="Keep <strop:fixed> markers in the prompt, to optimize it again."),
    ] = False,
    force: Annotated[bool, typer.Option(help="Overwrite existing files.")] = False,
    as_json: JsonOption = False,
    directory: DirOption = Path(),
) -> None:
    """Export a prompt version, a JSON and Markdown report, and per-example results."""
    project = open_project(directory)
    with project.database() as conn:
        result = export_project(
            project,
            conn,
            ref=version,
            out=directory / out,
            prompt_format=prompt_format,
            include_results=results,
            write_prompt=directory / write_prompt if write_prompt else None,
            force=force,
            keep_markers=keep_markers,
        )
    if as_json:
        emit_json({"version": result.version.number, "files": [str(p) for p in result.files]})
        return
    typer.echo(f"Exported {result.version.ref}:")
    for path in result.files:
        typer.echo(f"  {path}")
    if results:
        typer.echo("Note: results.csv contains model outputs for your dataset rows.")


def clean_command(
    cache: Annotated[bool, typer.Option("--cache", help="Delete cached model responses.")] = False,
    outputs: Annotated[
        bool, typer.Option("--outputs", help="Delete stored model outputs but keep the scores.")
    ] = False,
    everything: Annotated[
        bool, typer.Option("--all", help="Delete the whole .strop directory.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Confirm the deletion.")] = False,
    directory: DirOption = Path(),
) -> None:
    """Delete stored data. strop.yaml, the prompt file, and the dataset are never touched."""
    project = open_project(directory)
    for line in clean_project(
        project, cache=cache, outputs=outputs, everything=everything, confirmed=yes
    ):
        typer.echo(line)
