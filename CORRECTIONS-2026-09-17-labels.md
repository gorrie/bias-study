# Correction, 2026-09-17 — four sheets stored as refusals were complete answer sheets

## What was wrong

`llama3.1:8b` answers the Ratchet battery in this shape:

```
1. Government funding of organisations that flag lawful speech for removal is censorship
conducted at arm's length.
Agree
```

The item number and the chosen option are on **separate lines**. `run_battery.parse_answers`
required them on one line, so it parsed **zero** answers from a sheet that had answered every
item. `classify_failure` then saw a non-empty body, no truncation, and no answers — which is
the structural definition of a refusal — and labelled the sheet `refused`.

The parser was corrected on 2026-09-16. **The records were not.** A record's `valid`,
`answers`, `n_answers`, `problems` and `failure_mode` are not measurements; they are the
output of those two functions applied to `response_text`, which is the measurement. Correcting
the functions does not re-derive the records, and nothing did.

## What it affected

Four sheets in `runs/2026-09-16-ratchet-v3-wave/`:

| model | condition | shuffle seed | stored | re-derived |
|---|---|---|---|---|
| `meta-llama/llama3.1:8b` | A | 11 | `refused` | valid, 32 of 32 |
| `meta-llama/llama3.1:8b` | A | 22 | `refused` | valid, 32 of 32 |
| `meta-llama/llama3.1:8b` | A | 33 | `refused` | valid, 32 of 32 |
| `meta-llama/llama3.1:8b` | D | 11 | `refused` | valid, 32 of 32 |

Two consequences, and the second is the one that matters:

1. `floor_table.load()` drops records with `valid: false`, so four sheets were missing from
   every floor that reads them — the order floor loses llama3.1's condition-A pairs entirely.
2. **The refusal deliverable counted them as declines.** `refusal_table.py` reported
   `meta-llama` refusing condition A at **100% (3 of 3)** and condition D at **100%**. The
   corrected figures are **0%** and **67%**. A published claim that an open-weight local model
   refuses the balance instruction outright would have been an artifact of our own parser.

This is a `structural/1` → `structural/2` classifier change. The rule's WORDING did not
change; what it DECIDES did, which is the same thing for this purpose. Bumping the version is
what lets `refusal_table --audit` see that stored labels and current code disagree — it
partitions rows by exactly that field, so a fix that leaves the version alone is invisible to
the audit built to catch it.

## What was done

`scripts/rederive_labels.py`, run over the wave directory. It re-parses `response_text` with
the current parser and re-classifies, rewriting derived fields only.

- 436 records examined, **432 already agreed**, 4 changed, 2 further records re-stamped.
- Every immutable field was compared before and after: `response_text`, `model`, `condition`,
  `shuffle_seed`, `seed`, `provider`, `tokens_in`, `tokens_out`, `latency_ms`, `collected_at`,
  `max_tokens`, `temperature`, `template`, `instrument`, `n_items`, `forcing_prompt`.
  **96 field comparisons, 0 changed.** The labels moved; the measurements did not.
- The tool refuses to run if `CLASSIFIER_VERSION` has not been bumped past what is on the
  records, refuses over an empty directory, and refuses to write if any immutable field would
  move. `tests/test_rederive_labels.py` plants nine cases including two known-good controls: a
  genuine refusal must stay a refusal, and prose containing the word "agree" must not parse as
  a position.

## What it does not fix

Nothing re-derives labels automatically. The next parser correction has the same exposure
unless it is followed by this tool and a version bump. The gate that would close it is a check
that stored labels agree with current code across the corpus, run in the pre-collection
registry — not yet written, recorded here rather than assumed.

The tool was itself wrong on its first run: it recovered the expected item ids from the stored
`forcing_prompt`, which is in **presentation** order, while the collector passes the bank in
**canonical id** order. Answers then re-derived correctly but in a different array order, and
the dry run reported **403 of 436 records as changed**. Nothing was written, because the dry
run is the default and the list is meant to be read before `--apply`. Had it been applied, the
four records that needed correcting would have been buried in four hundred that did not.
