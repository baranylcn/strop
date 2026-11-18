# Strop

[![PyPI](https://img.shields.io/pypi/v/strop-cli)](https://pypi.org/project/strop-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/strop-cli)](https://pypi.org/project/strop-cli/)
[![CI](https://github.com/baranylcn/strop/actions/workflows/ci.yml/badge.svg)](https://github.com/baranylcn/strop/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/strop-cli)](https://github.com/baranylcn/strop/blob/main/LICENSE)

Strop is a command-line tool that improves LLM prompts by testing them against your own data. It runs your prompt, scores the outputs with a metric you define, asks a model to revise the prompt based on the failures, and keeps a revision only when the measured results get better.

## Status

Alpha. Commands and the `strop.yaml` format may change between releases.

## Documentation

The full documentation is at [baranylcn.github.io/strop](https://baranylcn.github.io/strop/).

## What it does

You give Strop a prompt, a dataset, and a definition of success. Strop then repeats this loop, for as many turns as you allow:

1. Score the current prompt on a validation set.
2. Run it on a separate training set and collect the failures, grouped by error type.
3. Ask an optimizer model for revised prompts that address those failures. Each revision must cite the examples that motivated it.
4. Score every revision on the same validation rows. Keep one only if the primary metric improves and none of your constraints is broken.
5. Start the next turn from the best prompt.

When the loop ends, you run the final prompt once on a held-out test set. Strop prints a colored diff between your original prompt and the final one.

Everything is local. Prompt versions, results, and cached model responses are stored in a `.strop/` directory inside your project. Strop has no server and no account, and it sends nothing anywhere except the model providers you configure.

## Install

Strop needs Python 3.11 or newer.

```bash
pip install strop-cli
strop --version
```

The package is called `strop-cli` on PyPI because the name `strop` is reserved there. The command it installs is `strop`. To keep Strop out of your other Python environments, install it with `pipx install strop-cli` instead. To work on Strop itself, see [Development](#development).

Shell completion for the `strop` command is available for bash, zsh, fish, and PowerShell. Run `strop --show-completion` to print the script, or `strop --install-completion` to add it to your shell configuration file. Strop changes that file only when you run `--install-completion`.

Strop calls models through [LiteLLM](https://docs.litellm.ai/docs/providers), so you can use any provider and model it supports. Set the API key your provider expects as an environment variable, or put it in a `.env` file in your project directory. Strop has no default model; you name every model yourself.

## Quick start

The [repository](https://github.com/baranylcn/strop) includes a ready-to-run example in `examples/ticket_routing`: 150 synthetic support tickets in five categories, with a deliberately vague starting prompt. Clone the repository to get it.

```bash
cd examples/ticket_routing

strop init \
  --name ticket-routing \
  --task "Route a customer message to a support category" \
  --prompt prompt.yaml \
  --data data.csv --id-column ticket_id \
  --input customer_message --expected category --metadata channel \
  --output-type label --labels billing,refund,exchange,technical,other \
  --metric macro_f1 --constraint "valid_output_rate>=0.98" \
  --target-model <provider/model> --optimizer-model <provider/model>
```

`strop init` writes `strop.yaml` and a `.strop/` directory, and tells you which providers will receive your dataset rows. Nothing is sent yet. Next, check and split the data:

```console
$ strop data check
Dataset: data.csv
Records: 150, valid: 150, invalid: 0
Columns: ticket_id, customer_message, category, channel

$ strop data split
Created split 1 (seed 42) over 150 rows:
  train      90
  validation 30
  test       30
```

The split is stored, so it never changes unless you ask for a new one. Now measure the starting prompt and start the loop:

```bash
strop baseline
strop optimize --max-turns 5
strop test --confirm
strop export
```

These commands call your models, so their output depends on which models you choose and is not shown here. `strop optimize` prints each turn as it goes and, at the end, the metric before and after, a table of every candidate and why it was kept or rejected, and the prompt diff. `strop export` writes the final prompt and a report to `exports/`.

## How success is measured

Strop cannot know what a correct output is. You define it, and Strop measures your definition.

| Way to define success | Use it when |
| --- | --- |
| Labeled data (`--expected`) | You have the right answer for each row: classification, extraction. |
| Rules (`--rule`) | You can check the output directly: length, required words, format. |
| A Python function (`--metric-file`) | You can compute a score in code. |
| A judge rubric (`--rubric-file`) | Quality needs judgment and there are no reference answers. |

Judge scores come from another language model, so they are estimates. Strop labels them as subjective and never mixes them with deterministic metrics. See the [metrics guide](https://baranylcn.github.io/strop/metrics/) for every metric and `examples/support_replies` for rules, a custom metric, and judge rubrics together.

## How a revision is accepted

A candidate becomes the best prompt only if the primary metric improves by a minimum amount, every constraint you set still holds, the share of valid outputs does not drop, no class loses more than a set amount of F1, and the candidate wins on more validation examples than it loses. Every failed rule is recorded with the candidate.

The test partition is locked in code. Nothing the optimizer sees comes from it, and `strop test` refuses to run without `--confirm`, or a second time without `--allow-rerun`, because tuning a prompt after looking at the test result makes the result optimistic. The [how it works guide](https://baranylcn.github.io/strop/how-it-works/) explains the rules in detail.

## Commands

| Command | Purpose |
| --- | --- |
| `strop init` | Create `strop.yaml`, a starter prompt, and the `.strop/` directory. |
| `strop data check` | Validate the dataset and list invalid rows with their row numbers. |
| `strop data split` | Create the train, validation, and test split. |
| `strop baseline` | Measure the initial prompt on the validation set. |
| `strop eval` | Score any prompt version on the train or validation set. Changes nothing. |
| `strop analyze` | Count and list how a prompt fails on the training data. |
| `strop optimize` | Run the optimization loop. Resumable. |
| `strop approve`, `strop reject` | Decide a candidate when running with `--approval manual`. |
| `strop test` | Run the final evaluation on the held-out test set. |
| `strop compare` | Run one prompt on several models and compare the results. |
| `strop diff`, `strop history` | Compare prompt versions and see every decision. |
| `strop prompt add`, `strop prompt show` | Save your own edit as a version, or print a version. |
| `strop rollback` | Make an earlier version the best prompt. Nothing is deleted. |
| `strop status` | Show the split, the best prompt, and recent evaluations. |
| `strop export` | Write the prompt, a JSON and Markdown report, and per-example results. |
| `strop clean` | Delete stored cache, outputs, or the whole `.strop/` directory. |

Run `strop <command> --help` for the options of each command. The commands never ask questions: every choice is a flag or a value in `strop.yaml`, so they work in scripts. Commands that print results accept `--json` for machine-readable output, and every command accepts `--dir` to name the project directory.

## Configuration

`strop init` writes `strop.yaml`. This is a minimal one:

```yaml
project:
  name: ticket-routing
  task_description: Route a customer message to a support category
dataset:
  path: data.csv
  columns: {customer_message: input, category: expected}
output:
  type: label
  labels: [billing, refund, exchange, technical, other]
models:
  target: {model: <provider/model>}
  optimizer: {model: <provider/model>}
metrics:
  primary: macro_f1
```

The prompt itself is a separate file with chat messages and a list of the messages the optimizer may change:

```yaml
messages:
  - role: system
    content: |-
      You route customer messages to a support team.
      Reply with the category only.
  - role: user
    content: |-
      Message: {{customer_message}}
optimize: [system]
```

The optimizer never touches messages outside `optimize`, never changes `{{variables}}`, and never changes text wrapped in `<strop:fixed>...</strop:fixed>`. Your file is not overwritten; revisions are stored as versions. The full reference is in the [configuration guide](https://baranylcn.github.io/strop/configuration/).

## Models and providers

The roles are `target` (the model your prompt is for), `optimizer` (proposes revisions), `analyzer` (proposes failure patterns, defaults to the optimizer), and `judge` (scores rubrics). Each can be a different provider and model. Model names are LiteLLM names, such as `<provider>/<model>`. Pass `--optimizer-model` or `--analyzer-model` to `strop optimize` to change a role for one run, and use `strop compare --models a,b` to compare target models on the same rows.

Strop retries temporary provider errors with exponential backoff. A call that still fails is recorded as an error for that one example and does not stop the run.

## Data and privacy

- Dataset rows go to the providers of the models you configure. The target model receives every row it is run on. The optimizer and analyzer receive a bounded sample of failed train examples. The judge receives each example it scores. `strop init` lists the providers.
- `evidence_examples` and `evidence_chars` in `strop.yaml` limit how much of the failed examples is shown to the optimizer and analyzer.
- Dataset content is always passed to models as quoted data, and the meta-prompts tell the models not to follow instructions found inside it.
- API keys are read from the environment or `.env` and are never stored by Strop. Key-like strings are removed from logs and provider error messages.
- `.strop/` holds model outputs and cached responses. Keep it and `.env` out of version control. `strop clean` deletes what you choose.
- A `metric.py` file is your own code and runs as written, in a separate process. Strop never executes anything found in a dataset.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success. |
| 1 | The command failed. |
| 2 | Usage or configuration error. |
| 10 | `strop optimize` paused and waits for `strop approve` or `strop reject`. |
| 11 | `strop optimize` stopped because a budget was reached. |
| 12 | The command was interrupted. Progress is saved. |

## Limitations

- A small validation set gives noisy comparisons. Strop warns below 30 validation rows and refuses to optimize below 10.
- The test set is only a fair estimate if you look at it once.
- Judge metrics are estimates, and a judge model can prefer its own style.
- The optimizer is a language model. It proposes revisions that fit the failures it is shown, and the validation rules decide whether they help. A revision that passes can still be tuned to the validation set, which is what the test set is for.
- Results depend on the models you use. A prompt tuned for one model may not transfer to another.
- Token and cost data come from the provider. When a provider reports none, Strop shows it as unavailable instead of estimating it.
- Strop optimizes single prompts, not agents or tool chains.

## Development

Strop uses [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/baranylcn/strop.git
cd strop
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

The tests use scripted models and make no network calls. See [CONTRIBUTING.md](https://github.com/baranylcn/strop/blob/main/CONTRIBUTING.md) for the project layout and conventions.

## License

MIT. See [LICENSE](https://github.com/baranylcn/strop/blob/main/LICENSE).
