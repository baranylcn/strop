from collections.abc import Sequence

import pytest

from strop.config.metrics import Bound, MetricsConfig
from strop.errors import ConfigError
from strop.metrics.registry import MetricContext, build_metric, known_metric_names
from strop.metrics.suite import MetricSuite
from strop.metrics.types import Direction, Example, Metric, MetricValue

CONTEXT = MetricContext(labels=("a", "b"))


def ex(expected: str, value: str | None) -> Example:
    return Example("r", {}, expected, value or "", value)


def test_build_metric_resolves_simple_and_parameterized_names() -> None:
    assert build_metric("macro_f1", CONTEXT).name == "macro_f1"
    assert build_metric("recall:a", CONTEXT).name == "recall:a"
    assert build_metric("weighted_precision", CONTEXT).name == "weighted_precision"


def test_unknown_metric_lists_the_available_names() -> None:
    with pytest.raises(ConfigError, match=r"unknown metric 'f2'.*macro_f1"):
        build_metric("f2", CONTEXT)


def test_misspelled_metric_suggests_the_closest_name() -> None:
    with pytest.raises(ConfigError, match=r"Did you mean 'macro_f1'\?.*Available: .*accuracy"):
        build_metric("macro_f2", CONTEXT)


def test_misspelled_parameterized_prefix_suggests_the_valid_prefix() -> None:
    with pytest.raises(ConfigError, match=r"Did you mean 'recall:refund'\?"):
        build_metric("recal:refund", CONTEXT)


def test_a_name_that_is_close_to_nothing_gets_no_suggestion() -> None:
    with pytest.raises(ConfigError) as error:
        build_metric("zzzzzz", CONTEXT)
    assert "Did you mean" not in str(error.value)
    assert "available: accuracy" in str(error.value)


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(ConfigError, match="unknown label"):
        build_metric("recall:z", CONTEXT)


def test_known_names_include_parameterized_forms() -> None:
    names = known_metric_names()
    assert "accuracy" in names
    assert "recall:<label>" in names


def test_suite_computes_primary_secondary_constraints_and_validity() -> None:
    config = MetricsConfig(
        primary="macro_f1",
        secondary=("accuracy",),
        constraints={"recall:a": Bound(min=0.9)},
    )
    suite = MetricSuite.from_config(config, CONTEXT)
    assert suite.names == ["macro_f1", "accuracy", "recall:a", "valid_output_rate"]
    report = suite.evaluate([ex("a", "a"), ex("b", "b"), ex("b", "a")])
    assert report.primary_value.value is not None
    assert report.values["accuracy"].value == pytest.approx(2 / 3)
    assert suite.direction("macro_f1") is Direction.MAXIMIZE


def test_violations_describe_each_broken_constraint() -> None:
    suite = MetricSuite.from_config(MetricsConfig(primary="accuracy"), CONTEXT)
    report = suite.evaluate([ex("a", "a"), ex("a", None)])
    problems = report.violations(
        {
            "valid_output_rate": Bound(min=0.98),
            "accuracy": Bound(max=0.9),
            "missing": Bound(min=1),
        }
    )
    assert problems == [
        "valid_output_rate is 0.5000, below the minimum 0.98",
        "missing could not be computed",
    ]
    assert report.violations({"accuracy": Bound(min=0.1)}) == []


def test_uncomputable_metric_is_a_violation() -> None:
    suite = MetricSuite.from_config(MetricsConfig(primary="accuracy"), CONTEXT)
    report = suite.evaluate([])
    assert report.violations({"accuracy": Bound(min=0.5)}) == ["accuracy could not be computed"]


class AlwaysOne(Metric):
    name = "custom"

    def compute(self, examples: Sequence[Example]) -> MetricValue:
        return self._result(1.0, len(examples))


def test_extra_metrics_override_builtin_resolution() -> None:
    config = MetricsConfig(primary="custom")
    suite = MetricSuite.from_config(config, CONTEXT, {"custom": AlwaysOne()})
    assert suite.evaluate([ex("a", "a")]).primary_value.value == 1.0
