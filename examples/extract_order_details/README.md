# Example: extracting order details

A structured extraction task. The dataset has 60 synthetic customer emails, each with the JSON
object a correct answer contains. All names, order numbers, and items are invented. The output
must be a JSON object that follows `schema.json`:

- `order_id`: the order number written in the email.
- `item`: the product the customer orders.
- `quantity`: how many, as an integer. Some emails write the number as a word.
- `express`: `true` only when the customer asks for express shipping.

Quality is measured by comparing each output with the expected object:

- `field_f1` (primary): F1 between the output's and the expected object's (field, value) pairs.
- `field_accuracy` (secondary): the share of expected fields whose value matches exactly.
- `schema_valid` (constraint): at least 90% of the outputs must satisfy `schema.json`.

Files:

- `data.jsonl`: `email_id`, `email`, and `expected` (a JSON object).
- `schema.json`: the JSON Schema of the output.
- `prompt.yaml`: the starting prompt. It is deliberately vague. Only the system message may be
  rewritten.

## Run it

Export the API keys your providers need.

```bash
cd examples/extract_order_details

strop init \
  --name extract-order-details \
  --task "Extract the order details from a customer email" \
  --prompt prompt.yaml \
  --data data.jsonl --id-column email_id \
  --input email --expected expected \
  --output-type json --output-schema schema.json \
  --metric field_f1 --secondary-metric field_accuracy \
  --constraint "schema_valid>=0.9" \
  --target-model <provider/model> \
  --optimizer-model <provider/model>

strop data check
strop data split
strop baseline
strop optimize --max-turns 5
strop test --confirm
strop export
```

`strop init`, `strop data check`, and `strop data split` do not call a model. With 60 rows the
validation set has 12, so `strop data split` warns that score differences may be noise. The results of the
other commands depend on the models you choose, so this example does not list expected scores.
