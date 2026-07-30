# satyrn-model

Fine-tune Qwen2.5-Coder-7B on PEP 750 template strings (t-strings) using
MLX LoRA on Apple Silicon.

## Pipeline

```bash
# 1. Generate verified training data (requires Python 3.14+)
python make_data.py

# 2. Train
python main.py

# 3. Evaluate the trained model
python eval.py
```

## Scripts

### `make_data.py` — generate and validate training data

Every candidate example is executed on the live interpreter and only written to
`data/pep750.jsonl` if it runs cleanly. Add new examples to the `EXAMPLES` list
at the top of the script.

```bash
python make_data.py                    # validate all examples, write JSONL
python make_data.py --validate-only    # validate all examples, no file write
python make_data.py -c "t'Hello {name}'"            # validate a single snippet
python make_data.py -c "..." -l "my test"           # with a custom label
```

| Flag | Description |
|------|-------------|
| `-v`, `--validate-only` | Run all examples through the interpreter, report pass/fail, don't write JSONL |
| `-c`, `--code` | Validate a single ad-hoc code snippet instead of built-in examples |
| `-l`, `--label` | Label for `--code` output (default: `<snippet>`) |

### `main.py` — train the model

Loads the JSONL via `datasets`, applies LoRA with Unsloth's MLX backend, and
trains with `MLXTrainer`. Saves the adapter to `./qwen2.5-coder-pep750/`.

```bash
python main.py
```

### `eval.py` — evaluate the trained model

Loads the fine-tuned adapter and generates code from prompts, then validates
each completion against the live Python 3.14 interpreter.

```bash
python eval.py                          # run all built-in eval prompts
python eval.py -p "..."                 # single ad-hoc prompt
python eval.py -n 3                     # first 3 built-in prompts only
python eval.py --no-validate            # skip validation, just print generations
python eval.py --max-tokens 512         # increase generation length
```

| Flag | Description |
|------|-------------|
| `-p`, `--prompt` | Single ad-hoc prompt to evaluate |
| `-n`, `--num-prompts` | Number of built-in prompts to evaluate (default: all) |
| `--no-validate` | Skip `exec()` validation — just print generated code |
| `--max-tokens` | Max tokens to generate (default: 256) |
