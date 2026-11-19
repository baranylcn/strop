# Changelog

All notable changes to Strop are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). While Strop is in alpha, minor versions may change
commands or the `strop.yaml` format.

## [Unreleased]

## [0.1.2] - 2026-11-19

### Added

- A documentation site at https://baranylcn.github.io/strop/, built with MkDocs Material and
  published from `docs/` to GitHub Pages.
- Colored terminal output: metrics, per-class scores, candidate statuses, score changes,
  warnings, and errors. A progress bar replaces the plain counter while model calls run.
- A STROP banner when you run `strop` without arguments or `strop init` in a terminal. Set
  `STROP_NO_BANNER=1` to hide it.

Color and the banner appear only in a terminal. Piped output, `--json`, and `NO_COLOR` stay plain.

### Fixed

- The data-recipient note in `strop init` names providers, and says so when a model name has no
  provider prefix. An unknown model id gets a hint to use the exact id from the provider.
- A blank line in a CSV dataset, such as an extra newline at the end of the file, is now skipped,
  as it already is in JSONL. Before, it was reported as an invalid row with 0 fields, so
  `strop data check` and the commands that load the dataset failed unless `--skip-invalid` was set.

## [0.1.1] - 2026-11-18

### Fixed

- An evaluation in which every model call failed (wrong API key, API base, or model name) is now
  an error with the first provider message. Before, it was stored and shown as a score of 0.
- The test report no longer shows a meaningless noise estimate of 0.00 for a perfect score. It
  shows a 95% Wilson interval for the score instead.
- `strop compare` keeps the results of working models when one model fails, marks the failed
  model, and no longer cuts long model names. The candidate table in the `optimize`
  summary shows why a candidate was rejected or discarded.
- A paused `optimize` run no longer says that no improvement was accepted while a candidate is
  waiting for approval.
- `strop history` shortens long summaries at a word boundary and marks the cut.

## [0.1.0] - 2026-11-18

First version.

### Added

- `strop init`, `strop data check`, and `strop data split` to set up a project and create a
  reproducible, optionally stratified train, validation, and test split.
- Prompt files with chat messages, `{{variables}}`, and `<strop:fixed>` spans. Immutable prompt
  versions with `strop prompt add`, `strop prompt show`, `strop diff`, `strop history`, and
  `strop rollback`.
- Metrics: classification scores, exact match, JSON validity and field-level scores, string
  similarity, numeric closeness, rule checks, custom Python metrics, and LLM judge rubrics.
- `strop baseline`, `strop eval`, `strop analyze`, and `strop status`.
- `strop optimize`: a resumable loop that analyzes train failures, proposes revised prompts,
  scores them on validation, and applies acceptance rules (minimum gain, constraints, valid
  output rate, per-class regression, paired comparison). Manual approval with `strop approve`
  and `strop reject`, budgets, and a colored diff between the initial and final prompt.
- `strop test` with a locked test partition, `strop compare` for several target models,
  `strop export` for prompts, JSON and Markdown reports, and per-example results, and
  `strop clean`.
- Any provider and model supported by LiteLLM, with retries, a response cache, and `.env` support.
