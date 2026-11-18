# Troubleshooting

Find the error from your terminal below. Numbers and values in angle brackets vary by run.

## Every model call failed

```text
every model call failed (N of N); first error: <detail>. Check the model name, the API key, the API base, and your network connection.
```

Every example in the evaluation returned a provider error, so Strop stopped without a score.
Start with the first error shown. Check the model name, API key, API base URL, and network
connection. After correcting the cause, retry the original command.

## The dataset file changed since the split was created

```text
the dataset file changed since the split was created; run 'strop data split' again
```

The current dataset's content hash differs from the one recorded in the active split. If you
edited the file on purpose, run `strop data check` and then `strop data split` to regenerate
the split. If the edit was accidental, restore the dataset used to create the active split.

## Invalid rows in the dataset

```text
N invalid row(s) in the dataset:
```

One or more rows failed validation. Run `strop data check` to see row numbers and errors, or
`strop data check --json` for the complete list. Fix the rows and run `strop data split` again.
To deliberately exclude the invalid rows, run `strop data split --skip-invalid`. Later
evaluations use the active split's setting.

## The validation partition has too few rows

```text
the validation partition has N rows, fewer than the M needed to compare prompts; add data
```

Optimization needs at least `optimization.min_validation_samples` validation rows to compare
prompts. Add valid labeled rows or adjust the [split ratios](configuration.md#split) to
allocate more rows to validation. Run `strop data split` again and check the validation count.
Keep the final test set held out from optimization.

## Too few rows for this split

```text
N rows are too few for this split: the <partition names> partition would be empty; add data or change the split ratios
```

A partition with a positive ratio would receive no rows. Add data or change the
[split ratios](configuration.md#split), then run `strop data split` again.

## The test partition was already used

```text
the test partition was already used (evaluation <id>, vN). Testing again after changing the prompt biases the result; pass --allow-rerun to continue anyway
```

The evaluation in the message already used this split's test partition. Refer to the saved
result, or use fresh held-out data for a new independent evaluation. To deliberately repeat
the test on this split, run `strop test --confirm --allow-rerun`. A repeat uses the same data
and can give a biased estimate if you changed the prompt after seeing the earlier result.

## A version is waiting for a decision

```text
vN is waiting for a decision; run 'strop approve vN' or 'strop reject vN' first
```

A candidate is pending manual approval. Inspect the candidate and use the version shown in
the message with `strop approve vN` or `strop reject vN`. Then run `strop optimize --resume`.
See [How it works](how-it-works.md) for the approval workflow.

## There is no unfinished run to resume

```text
there is no unfinished run to resume; start one with 'strop optimize'
```

The current project has no resumable run. Check that you are in the intended project. If you
want a new run, start it with `strop optimize`.
