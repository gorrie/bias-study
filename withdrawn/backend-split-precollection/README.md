# Pre-collection for the backend split — withdrawn from the panel, KEPT as evidence

**40 sheets, 196 records, collected 2026-09-16 through 2026-09-20 over OpenRouter.**

## Why this is in `withdrawn/`

These sheets were collected before the routing confound was understood, and they are not
analysable as a panel: the same model was served by **two to four different backends inside
one arm**, and 40 of the 196 records carry no `provider_pinned` value at all.

| model | distinct providers in this collection |
|---|---:|
| `deepseek/deepseek-v4-flash-0731` | 4 |
| `deepseek/deepseek-v4-pro-0813` | 4 |
| `moonshotai/kimi-k2.6` | 4 |
| `qwen/qwen3.8-2.4t-a95b` | 4 |
| `z-ai/glm-5.2` | 3 |
| `minimax/minimax-m2.7`, `moonshotai/kimi-k2-thinking`, `moonshotai/kimi-k2.5`, `xiaomi/mimo-v2.5-pro`, `z-ai/glm-5.1` | 2 each |

A condition difference measured across those sheets is a difference between *serving stacks*
as much as between conditions, which is the confound `PREREG-2026-09-14-i3-phase4.md`
line item 3 — "re-collect 4 backend-split models · removes the routing confound" — was
written to remove. The re-collection is what sits in `runs/`. This is what it replaced.

## Why it must NOT be deleted

**These records carry the LIVE instrument.** Not the retired questionnaire:

```
instrument   ratchet-battery      149 records
             ratchet-battery-v3    47 records
schema       battery-run/1        136 records
             compass-run/1         60 records   (the retired SCHEMA LABEL, not the retired instrument)
channel      openrouter           196 records
conditions   N 51 · A 53 · P 50 · D 42
```

On 2026-09-22 this directory was deleted along with the retired corpus, **because of the
directory it sat in rather than the records it holds** — 22 distinct providers of primary
evidence for the study's own serving-path finding, thrown out on a path match. It was
restored the same day. The test that should have been applied, and is the reason this file
exists:

> **Read the records, not the directory name.** `withdrawn/` means *out of the panel*. It does
> not mean *retired instrument*, and it never meant *deletable*.

The withdrawal is a **design** judgement — these sheets cannot answer the question the panel
asks — and a withdrawal that destroys its own evidence is not a withdrawal, it is a
disappearance. The whole point of the pre-registration line item is that a reader can see the
confound that motivated the re-collection. That requires the confounded sheets.

## What it is NOT

Not a result, not a floor, not comparable to anything in `runs/`, and out of every `runs/**`
glob by construction. Nothing in the paper is computed from it. It is cited, if at all, as the
thing that made the re-collection necessary.
