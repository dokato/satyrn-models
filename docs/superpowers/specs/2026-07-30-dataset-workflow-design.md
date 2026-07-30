# SP-DATASET: Measure-Harvest-Synthesize Dataset Workflow

Status: Approved for implementation by the user on 2026-07-30 (approach A plus
the machinery list, chosen over synthesis-first and retrieval-only).

Research of record: [`DATASET_METHODOLOGY.md`](../../../DATASET_METHODOLOGY.md)
— literature review, independent critical review, and two defects verified
against this repo. **Required pre-reading for every rung's brainstorm.**

## 1. Problem

satyrn-model is meant to teach a small local model Python 3.14/3.15 syntax that
postdates its pretraining. The current repo does not do that, and cannot
currently tell whether it does, for two verified reasons:

1. **Train/eval contamination.** Seven of ten prompts in `eval.py` are
   byte-identical to training descriptions in `make_data.py`; two more differ
   only cosmetically. At 24 examples and 3 epochs, the reported pass rate is a
   memorization score.
2. **The oracle cannot see the failure it exists to catch.** `validate_snippet`
   defines success as "did not raise." A completion answering a t-string task
   with an **f-string** passes, as does `pass`. Falling back to the pretrained
   form is the single most likely failure mode, and the harness is blind to it.

A third defect was environmental and is now **resolved**. The CPython source was
a *fork* (`t-strings/cpython`) on an in-progress docs branch dated 2025-06-17,
roughly four months pre-3.14.0, and it lacked `string.templatelib.convert()`
entirely — the canonical `!r`/`!s`/`!a` helper, and exactly the renderer idiom
this project exists to teach. Harvesting from it would have poisoned a dataset
whose entire purpose is currency. It has been replaced by a shallow clone of
official upstream `python/cpython` at tag `v3.14.5`
(`~/projects/pauleveritt/cpython-3.14.5`), matching the verifying interpreter.

The deeper problem is that no measurement loop is closed. Dataset size is not
the bottleneck; the absence of a number is. The user has confirmed the existing
scripts were placeholders and may be discarded.

## 2. Scope

**In scope.** A t-strings vertical slice, built end-to-end, with machinery
designed so additional 3.14/3.15 features plug in later:

- a held-out benchmark with hidden-test oracles, provably disjoint from every
  training corpus;
- a pytest-based verification harness with subprocess isolation and timeouts;
- a baseline ladder run through the existing local oMLX endpoint;
- a harvested corpus drawn from `tdom` and a freshly pinned CPython;
- one training run measured against those baselines;
- three project-local Claude skills encoding the conventions above.

**Out of scope for this spec.** Broad 3.14/3.15 feature coverage (deferred to
SP4, gated on this slice producing a measured win); synthesis machinery
(SP3, gated on harvest proving insufficient); the FIM-versus-chat deployment
decision (deliberately deferred — see §3.6).

**Explicitly discarded.** `main.py`, `make_data.py`, and `eval.py` in their
current form. They are placeholders and carry both defects above. Nothing in
this spec preserves their structure.

## 3. Decisions

### 3.1 Sequence is measure → harvest → synthesize, and the order is load-bearing

Each stage is gated on the previous stage's evidence. Measurement precedes data
work because the literature's own numbers argue against fine-tuning as the
default tool: documentation-in-context reaches ~66% executable on post-cutoff
API tasks, while the only weight-update result cited is negative. Harvesting
real code precedes synthesis because OSS-Instruct's central finding is that
seeding from real code beats ungrounded generation, and because harvesting is
nearly free here.

### 3.2 The baseline ladder is a decision gate, not a formality

SP1 produces three numbers on the held-out benchmark: base model zero-shot,
base model plus PEP 750 docs in context, and (later) the fine-tune.

> **Gate:** the fine-tune must beat base-plus-docs. If it does not, the correct
> answer for this project is a docs/retrieval layer, and that verdict is a
> legitimate outcome that re-scopes or kills the training track.

This is stated up front so the result cannot be rationalized after the fact.
It also means approach C (retrieval-only) is tested as a byproduct rather than
assumed to lose.

### 3.3 The oracle is pytest in a subprocess, never in-process `exec`

Verification runs each candidate as a pytest case in an isolated subprocess with
a timeout. This replaces `exec(compile(code, label, "exec"), {})`, which has no
timeout (a generated `while True` hangs the run), no isolation, and no notion of
a hidden test.

Every task carries three checks:

1. **Hidden asserts** the model never sees, expressing the task's actual
   contract.
2. **A feature-use check** — the solution must actually construct a `Template`.
3. **An old-form canary** — the task fails if the solution used an f-string or
   `.format()` where a template was required.

Checks 2 and 3 exist specifically because "did not raise" cannot distinguish a
correct answer from a pretrained-prior fallback.

### 3.4 Every example records its provenance and source version

Each corpus row carries the source file, the upstream commit or tag it came
from, and the interpreter version that verified it.

**Pin to the version that verifies, not to the newest.** CPython is pinned at
`v3.14.5` because that matches the installed interpreter which executes every
example — deliberately not upstream's newer `v3.14.6`, so harvest source and
validator cannot drift apart. `main` is used only for 3.15 material, recorded as
such. Sources must come from official upstream (`python/cpython`), never a fork.

This is a direct response to the stale-checkout near-miss. A dataset whose
purpose is currency is uniquely damaged by an unlabelled stale snapshot, and
provenance makes the failure detectable instead of silent. The near-miss also
produced a second lesson worth encoding: the *first* diagnosis of that staleness
was wrong on the facts (see the correction recorded in the research doc), which
is why SP2 R1 makes the pin machine-enforced rather than trusting a written
claim about what a tree contains.

### 3.5 Harvest converts real code into tasks; it does not paraphrase it

The unit of harvest is a real function from `tdom` or CPython: its signature and
docstring become the prompt, its body the reference solution, and its existing
tests the hidden oracle. `tdom` uses a `*_test.py` suffix (not `test_*.py`), so
naive test discovery finds nothing — the harvester must know this.

`tdom` is the highest-value source because it is a real library *consuming* the
feature rather than demonstrating it, exercising precisely the renderer idiom
(a processing function over `.strings` / `.interpolations`) that the model
lacks. `processor_test.py` alone is 78 KB.

### 3.6 The corpus is stored format-neutral

Rows are stored as structured records — task, reference solution, hidden tests,
provenance — and rendered to a training format at training time. The
FIM-versus-chat deployment decision is deferred rather than baked in, because it
is genuinely undecided and because format-neutral storage costs little and
permits training both and comparing.

### 3.7 Training uses mlx-lm directly

Unsloth's MLX backend is new, and its rank/alpha handling and prompt-token loss
masking are unverified. `mlx-lm` is the lower-level, better-understood path on
hardware that is already running MLX via oMLX. Rank is a swept parameter, not a
guessed constant; note that the placeholder config paired `r=16` with
`alpha=16`, so any rank change must adjust alpha deliberately.

### 3.8 Conventions ship as project-local Claude skills

Three skills in `.claude/skills/`, written when the convention they encode is
first established, not speculatively:

- `harvest-corpus` — extraction rules, the `*_test.py` suffix trap, mandatory
  version pinning and provenance;
- `verify-example` — the three-check oracle contract of §3.3;
- `eval-run` — running the ladder, reading it, and the contamination check.

## 4. Completion criteria

This spec is satisfied when all of the following hold:

- A held-out benchmark exists whose tasks are provably disjoint from every
  training corpus, enforced by an automated contamination check that fails loudly
  rather than reporting a score.
- The oracle runs candidates as isolated, timed-out pytest cases and applies all
  three checks; a deliberately planted f-string solution to a template task is
  demonstrated to **fail**.
- Three baseline numbers exist for the benchmark: base zero-shot, base plus docs,
  and at least one fine-tune, all produced by the same harness.
- A base-model audit has compared at least two candidate bases zero-shot, and the
  chosen base is recorded with its reasoning.
- The harvested corpus draws from `tdom` and the official-upstream CPython
  checkout pinned at `v3.14.5`, with per-row provenance, and the harvester
  *enforces* the pin by failing when the tree's tag and the verifying
  interpreter disagree.
- One training run has completed and been scored against the baselines, and the
  §3.2 gate has been evaluated and its verdict recorded — including if the verdict
  is that retrieval wins.
- The three project-local skills exist and encode the conventions actually used.

**Non-criteria.** Beating the baseline is *not* a completion criterion. Producing
a trustworthy number is. A well-measured negative result closes this spec
successfully and re-scopes the roadmap.
