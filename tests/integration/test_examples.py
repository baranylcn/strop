"""The shipped examples must keep working with the commands their READMEs show."""

import shutil
from pathlib import Path

import pytest

import strop
from tests.helpers import CliRunner

EXAMPLES = Path(strop.__file__).resolve().parents[2] / "examples"

pytestmark = pytest.mark.skipif(not EXAMPLES.is_dir(), reason="examples are not in this checkout")


def copy_example(name: str, destination: Path) -> Path:
    shutil.copytree(EXAMPLES / name, destination, dirs_exist_ok=True)
    return destination


def test_ticket_routing_example(run_cli: CliRunner, tmp_path: Path) -> None:
    project = copy_example("ticket_routing", tmp_path)
    code, _, err = run_cli(
        "init", "--dir", str(project), "--name", "ticket-routing",
        "--task", "Route a customer message to a support category",
        "--prompt", "prompt.yaml", "--data", "data.csv", "--id-column", "ticket_id",
        "--input", "customer_message", "--expected", "category", "--metadata", "channel",
        "--output-type", "label", "--labels", "billing,refund,exchange,technical,other",
        "--metric", "macro_f1", "--constraint", "valid_output_rate>=0.98",
        "--target-model", "openai/example", "--optimizer-model", "anthropic/example",
    )  # fmt: skip
    assert code == 0, err
    code, out, _ = run_cli("data", "check", "--dir", str(project))
    assert code == 0
    assert "Records: 150, valid: 150, invalid: 0" in out
    assert "Labels: billing 30, exchange 30, other 30, refund 30, technical 30" in out
    code, out, _ = run_cli("data", "split", "--dir", str(project))
    assert code == 0
    assert "train      90" in out
    assert "validation 30" in out
    assert "Warning" not in out


def test_support_replies_example(run_cli: CliRunner, tmp_path: Path) -> None:
    project = copy_example("support_replies", tmp_path)
    code, _, err = run_cli(
        "init", "--dir", str(project), "--name", "support-replies",
        "--task", "Answer a customer question for an online shop",
        "--prompt", "prompt.yaml", "--data", "data.csv", "--id-column", "question_id",
        "--input", "question", "--metadata", "topic", "--output-type", "text",
        "--rubric-file", "rubric.yaml", "--metric-file", "metric.py",
        "--rule", "short=max_words:120", "--rule", "no_promises=not_matches:(?i)guarantee",
        "--metric", "judge:helpful", "--secondary-metric", "judge:polite",
        "--constraint", "rule:short>=0.95",
        "--target-model", "openai/example", "--optimizer-model", "anthropic/example",
        "--judge-model", "google/example",
    )  # fmt: skip
    assert code == 0, err
    code, out, _ = run_cli("data", "split", "--dir", str(project))
    assert code == 0
    assert "validation 12" in out
