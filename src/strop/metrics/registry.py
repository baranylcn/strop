"""Resolving metric names from strop.yaml to metric objects."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from difflib import get_close_matches

from strop.config.metrics import RuleSpec
from strop.errors import ConfigError
from strop.metrics.basic import ExactMatch, ValidOutputRate
from strop.metrics.classification import Accuracy, Average, Averaged, ClassScore, Kind
from strop.metrics.rules import RuleMetric
from strop.metrics.structured import (
    FieldAccuracy,
    FieldCompleteness,
    FieldF1,
    JsonValid,
    SchemaValid,
)
from strop.metrics.text import NumericClose, Similarity
from strop.metrics.types import Metric

_AVERAGES: tuple[Average, ...] = ("macro", "micro", "weighted")
_KINDS: tuple[Kind, ...] = ("precision", "recall", "f1")


@dataclass(frozen=True)
class MetricContext:
    """What metric constructors need to know about the task."""

    labels: tuple[str, ...] = ()
    rules: Mapping[str, RuleSpec] = field(default_factory=dict)


Factory = Callable[[MetricContext], Metric]
ParamFactory = Callable[[str, MetricContext], Metric]


def _averaged_factory(average: Average, kind: Kind) -> Factory:
    return lambda ctx: Averaged(average, kind, ctx.labels)


def _simple_factories() -> dict[str, Factory]:
    factories: dict[str, Factory] = {
        "accuracy": lambda ctx: Accuracy(ctx.labels),
        "exact_match": lambda ctx: ExactMatch(),
        "valid_output_rate": lambda ctx: ValidOutputRate(),
        "json_valid": lambda ctx: JsonValid(),
        "schema_valid": lambda ctx: SchemaValid(),
        "field_completeness": lambda ctx: FieldCompleteness(),
        "field_accuracy": lambda ctx: FieldAccuracy(),
        "field_f1": lambda ctx: FieldF1(),
        "similarity": lambda ctx: Similarity(),
        "numeric_close": lambda ctx: NumericClose(),
    }
    for average in _AVERAGES:
        for kind in _KINDS:
            factories[f"{average}_{kind}"] = _averaged_factory(average, kind)
    return factories


def _class_factory(kind: Kind) -> ParamFactory:
    def build(label: str, ctx: MetricContext) -> Metric:
        if ctx.labels and label not in ctx.labels:
            raise ConfigError(
                f"metric '{kind}:{label}' names an unknown label; labels: {', '.join(ctx.labels)}"
            )
        return ClassScore(kind, label, ctx.labels)

    return build


def _rule_factory(name: str, ctx: MetricContext) -> Metric:
    if name not in ctx.rules:
        defined = ", ".join(ctx.rules) or "none"
        raise ConfigError(f"rule '{name}' is not defined under metrics.rules; defined: {defined}")
    return RuleMetric(name, ctx.rules[name])


def _numeric_close_factory(tolerance: str, ctx: MetricContext) -> Metric:
    try:
        return NumericClose(float(tolerance))
    except ValueError:
        raise ConfigError(f"metric 'numeric_close:{tolerance}' needs a numeric tolerance") from None


_SIMPLE = _simple_factories()
_PARAMETERIZED: dict[str, ParamFactory] = {
    **{kind: _class_factory(kind) for kind in _KINDS},
    "rule": _rule_factory,
    "numeric_close": _numeric_close_factory,
}


def known_metric_names() -> list[str]:
    """Built-in metric names, plus the parameterized forms."""
    return sorted(_SIMPLE) + [f"{prefix}:<label>" for prefix in sorted(_PARAMETERIZED)]


def register_parameterized(prefix: str, factory: ParamFactory) -> None:
    """Add a metric family addressed as ``<prefix>:<argument>``."""
    _PARAMETERIZED[prefix] = factory


def register(name: str, factory: Factory) -> None:
    """Add a built-in metric addressed by ``name``."""
    _SIMPLE[name] = factory


def build_metric(name: str, context: MetricContext) -> Metric:
    """Create the metric called ``name`` or raise ``ConfigError`` listing the valid names."""
    if name in _SIMPLE:
        return _SIMPLE[name](context)
    prefix, separator, argument = name.partition(":")
    if separator and argument and prefix in _PARAMETERIZED:
        return _PARAMETERIZED[prefix](argument, context)
    raise ConfigError(_unknown_metric_message(name, prefix, separator, argument))


def _suggestion(name: str, prefix: str, separator: str, argument: str) -> str | None:
    """The closest valid metric name to ``name``, or None when nothing is close."""
    if separator and argument:
        close = get_close_matches(prefix, _PARAMETERIZED, n=1)
        return f"{close[0]}:{argument}" if close else None
    close = get_close_matches(name, _SIMPLE, n=1)
    return close[0] if close else None


def _unknown_metric_message(name: str, prefix: str, separator: str, argument: str) -> str:
    available = ", ".join(known_metric_names())
    suggestion = _suggestion(name, prefix, separator, argument)
    if suggestion is None:
        return f"unknown metric '{name}'; available: {available}"
    return f"unknown metric '{name}'. Did you mean '{suggestion}'? Available: {available}"
