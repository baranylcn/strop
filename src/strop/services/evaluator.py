"""Evaluating prompt versions on dataset partitions and storing the results."""

import hashlib
import json
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from strop.config.enums import ModelRole
from strop.config.llm import ModelSpec
from strop.data.models import Partition, Row
from strop.errors import DataError, LLMError
from strop.evaluation.budget import BudgetTracker
from strop.evaluation.budgeted import BudgetedClient
from strop.evaluation.examples import to_examples, with_scores
from strop.evaluation.models import EvaluationRecord, ExampleOutcome, NewEvaluation
from strop.evaluation.parsing import load_output_schema
from strop.evaluation.runner import Progress, PromptRunner
from strop.llm.client import LLMClient
from strop.llm.factory import build_client
from strop.log import LOGGER_NAME
from strop.metrics.suite import MetricSuite
from strop.metrics.types import ErrorCode
from strop.prompts.versions import PromptVersion
from strop.services.metrics import build_suite, judge_model
from strop.services.partitions import PartitionedData, load_partitions
from strop.services.project import Project
from strop.storage.cache import ResponseCache
from strop.storage.datasets import DatasetRepository
from strop.storage.evaluations import EvaluationRepository

LOG = logging.getLogger(LOGGER_NAME)


@dataclass(frozen=True)
class RunTag:
    """Labels an evaluation: what it is for, free-form details, and its optimization run."""

    kind: str
    details: dict[str, Any] = field(default_factory=dict)
    run_id: int | None = None


@dataclass(frozen=True)
class Evaluator:
    """Runs prompt versions against partitions and persists each evaluation.

    The test partition is refused unless the evaluator was created with ``allow_test``;
    only the final ``strop test`` step does that.
    """

    project: Project
    partitions: PartitionedData
    suite: MetricSuite
    client: LLMClient
    repository: EvaluationRepository
    budget: BudgetTracker
    target: ModelSpec
    schema: dict[str, Any] | None = None
    allow_test: bool = False

    def fingerprint(self) -> str:
        """Hash of every setting that changes what an evaluation measures."""
        config = self.project.config
        payload = {
            "target": self.target.model_dump(mode="json"),
            "output": config.output.model_dump(mode="json"),
            "metrics": config.metrics.model_dump(mode="json"),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def reusable(self, version: PromptVersion, partition: Partition) -> EvaluationRecord | None:
        """A stored full-partition evaluation of ``version`` made under the same settings."""
        expected = len(self.partitions.get(partition))
        for record in self.repository.find(
            prompt_number=version.number, partition=partition, limit=50
        ):
            if (
                record.split_id == self.partitions.split_id
                and record.sample_count == expected
                and not record.details.get("sampled")
                and record.details.get("fingerprint") == self.fingerprint()
            ):
                return record
        return None

    def rows(self, partition: Partition) -> list[Row]:
        if partition is Partition.TEST and not self.allow_test:
            raise DataError("the test partition is locked; it is only used by 'strop test'")
        return self.partitions.get(partition)

    async def evaluate(
        self,
        version: PromptVersion,
        partition: Partition,
        tag: RunTag,
        *,
        rows: Sequence[Row] | None = None,
        progress: Progress | None = None,
    ) -> EvaluationRecord:
        """Evaluate ``version`` on ``partition`` (or a subset of its rows) and store the result."""
        selected = list(rows) if rows is not None else self.rows(partition)
        if rows is not None:
            self.rows(partition)  # enforces the test lock for explicit subsets too
        config = self.project.config
        runner = PromptRunner(
            self.client,
            self.target,
            config.output,
            self.schema,
            config.execution,
            self.budget,
        )
        outcomes = await runner.run(version.template, selected, progress)
        _require_some_answers(outcomes)
        examples = to_examples(selected, outcomes)
        await self.suite.prepare(examples)
        report = self.suite.evaluate(examples)
        return self.repository.save(
            NewEvaluation(
                prompt_number=version.number,
                split_id=self.partitions.split_id,
                partition=partition,
                kind=tag.kind,
                report=report,
                outcomes=with_scores(outcomes, examples, self.suite),
                details={
                    "model": self.target.model,
                    "fingerprint": self.fingerprint(),
                    **tag.details,
                },
                run_id=tag.run_id,
            )
        )


def _require_some_answers(outcomes: Sequence[ExampleOutcome]) -> None:
    """An evaluation where every call failed measures nothing, so it is an error, not a score."""
    if outcomes and all(o.error == ErrorCode.PROVIDER_ERROR for o in outcomes):
        first = outcomes[0].detail or ""
        hint = (
            " The provider does not know this model name; use the exact id from its model list."
            if "NotFound" in first or "not_found" in first
            else ""
        )
        raise LLMError(
            f"every model call failed ({len(outcomes)} of {len(outcomes)}); first error: "
            f"{(outcomes[0].detail or 'unknown').rstrip('.')}. Check the model name, the API key, "
            f"the API base, and your network connection.{hint}"
        )


def build_evaluator(
    project: Project,
    conn: sqlite3.Connection,
    *,
    use_cache: bool = True,
    allow_test: bool = False,
    budget: BudgetTracker | None = None,
) -> Evaluator:
    """Assemble an evaluator from the project configuration and an open database."""
    config = project.config
    tracker = budget or BudgetTracker(config.budgets)
    cache = ResponseCache(conn) if use_cache else None
    judge_spec = judge_model(project)
    judge = None
    if judge_spec is not None:
        judge_client = BudgetedClient(build_client(config.execution, cache), tracker)
        judge = (judge_client, judge_spec)
        if judge_spec.model == config.models.target.model:
            LOG.warning(
                "the judge model is the same as the target model; its scores may favor its "
                "own style. Use a different judge model if you can."
            )
    return Evaluator(
        project=project,
        partitions=load_partitions(project, DatasetRepository(conn)),
        suite=build_suite(project, judge),
        client=build_client(config.execution, cache),
        repository=EvaluationRepository(conn),
        budget=tracker,
        target=config.models.resolve(ModelRole.TARGET),
        schema=load_output_schema(project.root, config.output),
        allow_test=allow_test,
    )
