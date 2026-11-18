"""What happens when the model provider fails."""

import json
import sqlite3
from pathlib import Path

import pytest

from strop.errors import LLMError
from strop.llm import LLMRequest, MockLLMClient
from tests.helpers import CliRunner


def install(monkeypatch: pytest.MonkeyPatch, client: MockLLMClient) -> None:
    for module in ("evaluator", "context", "evaluate", "analysis"):
        monkeypatch.setattr(
            f"strop.services.{module}.build_client", lambda *_: client, raising=False
        )


def always_down(request: LLMRequest) -> str:
    raise LLMError("APIConnectionError: connection refused")


def test_a_run_where_every_call_fails_is_an_error_and_stores_nothing(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, MockLLMClient(always_down))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, out, err = run_cli("baseline", "--dir", str(project))
    assert code == 1
    assert "every model call failed (20 of 20)" in err
    assert "connection refused" in err
    assert "Output problems" not in out
    conn = sqlite3.connect(project / ".strop" / "strop.db")
    assert conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 0


def test_optimize_fails_clearly_and_marks_the_run_failed(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, MockLLMClient(always_down))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, _, err = run_cli("optimize", "--dir", str(project))
    assert code == 1
    assert "every model call failed" in err
    conn = sqlite3.connect(project / ".strop" / "strop.db")
    assert conn.execute("SELECT status FROM runs").fetchall() == [("failed",)]


def test_some_failed_calls_are_recorded_and_the_run_continues(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"n": 0}

    def flaky(request: LLMRequest) -> str:
        calls["n"] += 1
        if calls["n"] % 4 == 0:
            raise LLMError("temporary outage")
        return "refund"

    install(monkeypatch, MockLLMClient(flaky))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, out, _ = run_cli("baseline", "--dir", str(project))
    assert code == 0
    assert "provider_error 5" in out


def test_compare_does_not_truncate_long_model_names(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, MockLLMClient("refund"))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    long_name = "provider/a-model-with-a-rather-long-name-for-this-test"
    code, out, _ = run_cli(
        "compare", "--dir", str(project), "--models", f"{long_name},provider/short"
    )
    assert code == 0
    assert chr(0x2026) not in out


def test_compare_keeps_working_models_when_one_model_fails(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def route(request: LLMRequest) -> str:
        if request.model == "provider/broken":
            raise LLMError("no access to this model")
        return "refund"

    install(monkeypatch, MockLLMClient(route))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, out, _ = run_cli(
        "compare", "--dir", str(project), "--models", "provider/good,provider/broken"
    )
    assert code == 0
    assert "provider/good" in out
    assert "provider/broken" in out
    assert "failed" in out
    assert "no access to this model" in out
    _, raw, _ = run_cli(
        "compare", "--dir", str(project), "--models", "provider/good,provider/broken", "--json"
    )
    models = {m["model"]: m for m in json.loads(raw)["models"]}
    assert "error" in models["provider/broken"]
    assert models["provider/good"]["partition"] == "validation"


def test_compare_fails_when_no_model_works(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, MockLLMClient(always_down))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, _, err = run_cli("compare", "--dir", str(project), "--models", "a/x,b/y")
    assert code == 1
    assert "no model could be evaluated" in err


def test_an_unknown_model_name_gets_a_specific_hint(
    run_cli: CliRunner, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def not_found(request: LLMRequest) -> str:
        raise LLMError('NotFoundError: {"type":"not_found_error","message":"model: claude-x.5"}')

    install(monkeypatch, MockLLMClient(not_found))
    assert run_cli("data", "split", "--dir", str(project))[0] == 0
    code, _, err = run_cli("baseline", "--dir", str(project))
    assert code == 1
    assert "does not know this model name" in err
    assert "exact id from its model list" in err
