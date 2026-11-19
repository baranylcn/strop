import json

import pytest

from strop.prompts import PromptMessage, PromptTemplate, dump_prompt, parse_prompt
from strop.prompts.versions import PromptVersion
from strop.reporting.prompt_export import PromptFormat, render_prompt

SYSTEM = "Classify.\nUse <strop:fixed>exact labels</strop:fixed>.\n"
CLEAN_SYSTEM = "Classify.\nUse exact labels.\n"
TEMPLATE = PromptTemplate(
    (PromptMessage("system", SYSTEM), PromptMessage("user", "Text: {{text}}")),
    frozenset({"system"}),
)
VERSION = PromptVersion(3, 1, TEMPLATE, "clarify labels", "run 1", "optimizer", "2026-01-01")


def test_yaml_export_with_markers_loads_back_to_the_same_template() -> None:
    text = render_prompt(VERSION, PromptFormat.YAML, keep_markers=True)
    assert parse_prompt(text, ".yaml") == TEMPLATE


@pytest.mark.parametrize("fmt", list(PromptFormat))
def test_exports_have_no_fixed_markers_by_default(fmt: PromptFormat) -> None:
    text = render_prompt(VERSION, fmt)
    assert "strop:fixed" not in text
    assert "exact labels" in text


@pytest.mark.parametrize("fmt", list(PromptFormat))
def test_markers_stay_when_asked(fmt: PromptFormat) -> None:
    text = render_prompt(VERSION, fmt, keep_markers=True)
    assert "<strop:fixed>exact labels</strop:fixed>" in text


def test_stripped_yaml_keeps_the_editable_roles() -> None:
    loaded = parse_prompt(render_prompt(VERSION, PromptFormat.YAML), ".yaml")
    assert loaded.optimize == TEMPLATE.optimize
    assert "Use exact labels." in loaded.messages[0].content
    assert "strop:fixed" not in loaded.messages[0].content


@pytest.mark.parametrize(
    "content",
    [
        "no trailing newline",
        "trailing newline\n",
        "two trailing newlines\n\n",
        "  leading spaces\nand a second line",
        "line one\n\nline three: with colon",
        "quotes \" and ' and backslash \\ and {{var}}",
        "- looks like a list\n# and a comment",
    ],
)
def test_prompt_yaml_round_trips_exactly(content: str) -> None:
    template = PromptTemplate((PromptMessage("system", content),), frozenset({"system"}))
    assert parse_prompt(dump_prompt(template), ".yaml") == template


def test_markdown_contains_every_message_verbatim() -> None:
    text = render_prompt(VERSION, PromptFormat.MD)
    assert text.startswith("# Prompt v3\n")
    assert "- Parent: v1" in text
    assert "- Variables: `{{text}}`" in text
    assert "## system (message 1, editable)" in text
    assert "## user (message 2, frozen)" in text
    assert CLEAN_SYSTEM.rstrip("\n") in text
    assert "Text: {{text}}" in text


def test_markdown_uses_a_longer_fence_when_the_prompt_contains_one() -> None:
    template = PromptTemplate(
        (PromptMessage("user", "Reply in a ```json block"),), frozenset({"user"})
    )
    version = PromptVersion(1, None, template, "", "", "user", "")
    assert "````text" in render_prompt(version, PromptFormat.MD)


def test_text_export_labels_each_role() -> None:
    text = render_prompt(VERSION, PromptFormat.TXT)
    assert text.startswith("[system]\nClassify.")
    assert "\n\n[user]\nText: {{text}}" in text


def test_json_export_describes_the_version() -> None:
    payload = json.loads(render_prompt(VERSION, PromptFormat.JSON))
    assert payload["version"] == 3
    assert payload["variables"] == ["text"]
    assert [m["editable"] for m in payload["messages"]] == [True, False]
    assert payload["messages"][0]["content"] == CLEAN_SYSTEM
