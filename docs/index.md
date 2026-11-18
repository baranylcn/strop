# Strop

Strop is a command-line tool that improves LLM prompts by testing them against your own data. It
runs your prompt, scores the outputs with a metric you define, asks a model to revise the prompt
based on the failures, and keeps a revision only when the measured results get better.

## Install

Strop needs Python 3.11 or newer.

```bash
pip install strop-cli
strop --version
```

The package is called `strop-cli` on PyPI because the name `strop` is reserved there. The command
it installs is `strop`.

Strop calls models through [LiteLLM](https://docs.litellm.ai/docs/providers), so you can use any
provider and model it supports. Set the API key your provider expects as an environment variable,
or put it in a `.env` file in your project directory. Strop has no default model; you name every
model yourself.

## The loop

You give Strop a prompt, a dataset, and a definition of success. It then repeats this, for as many
turns as you allow:

1. Score the current prompt on a validation set.
2. Run it on a separate training set and collect the failures, grouped by error type.
3. Ask an optimizer model for revised prompts that address those failures. Each revision must cite
   the examples that motivated it.
4. Score every revision on the same validation rows. Keep one only if the primary metric improves
   and none of your constraints is broken.
5. Start the next turn from the best prompt.

When the loop ends, you run the final prompt once on a held-out test set. Strop prints a colored
diff between your original prompt and the final one.

## Try it

The repository includes three runnable examples, `examples/ticket_routing` (labeled
classification), `examples/support_replies` (rules, a custom metric, and judge rubrics), and
`examples/extract_order_details` (JSON extraction with a schema and field-level metrics). Clone the
[repository](https://github.com/baranylcn/strop) to get them, then follow the README in each
folder.

```bash
strop init --name ticket-routing --task "Route a customer message to a support category" \
  --prompt prompt.yaml --data data.csv --id-column ticket_id \
  --input customer_message --expected category \
  --output-type label --labels billing,refund,exchange,technical,other \
  --metric macro_f1 \
  --target-model <provider/model> --optimizer-model <provider/model>
strop data split
strop baseline
strop optimize --max-turns 5
strop test --confirm
strop export
```

## Where to go next

- [How it works](how-it-works.md): the three partitions, one turn of the loop, the rules that
  accept or reject a revision, and what stays on your machine.
- [Configuration](configuration.md): every key in `strop.yaml` and the prompt file format.
- [Metrics](metrics.md): every built-in metric, rules, custom Python metrics, and judge rubrics.

The source, the issue tracker, and the changelog are on
[GitHub](https://github.com/baranylcn/strop).
