"""Exporting a stored prompt version as Markdown, plain text, JSON, or Strop prompt YAML."""

import json
from enum import StrEnum

from strop.prompts import PromptTemplate, dump_prompt
from strop.prompts.versions import PromptVersion


class PromptFormat(StrEnum):
    MD = "md"
    TXT = "txt"
    JSON = "json"
    YAML = "yaml"


def render_prompt(version: PromptVersion, fmt: PromptFormat, *, keep_markers: bool = False) -> str:
    """The prompt messages in the requested format.

    ``<strop:fixed>`` markers only matter to Strop, so they are removed unless ``keep_markers``
    is set; the text inside them stays. Keep them when the file will be optimized again.
    """
    template = version.template if keep_markers else version.template.without_markers()
    if fmt is PromptFormat.YAML:
        return dump_prompt(template)
    if fmt is PromptFormat.JSON:
        return json.dumps(prompt_payload(version, template), indent=2, ensure_ascii=False) + "\n"
    if fmt is PromptFormat.TXT:
        return "\n\n".join(f"[{m.role}]\n{m.content}" for m in template.messages) + "\n"
    return _markdown(version, template)


def prompt_payload(
    version: PromptVersion, template: PromptTemplate | None = None
) -> dict[str, object]:
    template = template or version.template
    return {
        "version": version.number,
        "parent": version.parent_number,
        "source": version.source,
        "change_summary": version.change_summary,
        "variables": list(template.variables),
        "messages": [
            {"role": m.role, "content": m.content, "editable": template.is_editable(m)}
            for m in template.messages
        ],
    }


def _markdown(version: PromptVersion, template: PromptTemplate) -> str:
    lines = [f"# Prompt {version.ref}", ""]
    if version.parent_number:
        lines.append(f"- Parent: v{version.parent_number}")
    lines.append(f"- Source: {version.source}")
    if template.variables:
        lines.append("- Variables: " + ", ".join(f"`{{{{{v}}}}}`" for v in template.variables))
    if version.change_summary:
        lines.append(f"- Summary: {version.change_summary}")
    for index, message in enumerate(template.messages, 1):
        state = "editable" if template.is_editable(message) else "frozen"
        fence = "````" if "```" in message.content else "```"
        lines += ["", f"## {message.role} (message {index}, {state})", "", f"{fence}text"]
        lines += [message.content.rstrip("\n"), fence]
    return "\n".join(lines) + "\n"
