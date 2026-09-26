# Pre-registration — completing the wave's short cells

**Registered 2026-09-25, before any sheet in this arm is collected.** Nothing below may be
amended after the first call; an amendment made after that is recorded as an amendment, dated,
with the reason, and the original text is left standing.

---

## Why

Three sets of wave cells came back short, and the paper discloses each (§5.4, §5.7):

- **`z-ai/glm-5.2`** returned nothing for conditions B, C and E and for the clause-factorial
  cells it was opened on (F000, F001, F010), and was never opened on the other five. Its pin was
  to a backend that stopped serving it (25 HTTP 404s in 27 hours). So the factorial ran on seven
  models of the eight `PREREG-2026-08-31-clause-factorial.md` names.
- **`google/gemini-3.8-flash`** is one of the four models whose refusal varies across the
  factorial's cells, and the only one of the four collected at a single presentation order. It
  therefore has no between-order floor, and the factorial's per-clause verdicts rest on the other
  three (`PREREG-2026-09-25-factorial-floor-calibration.md`).
- **`hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M`**, a local build, returned
  nothing for conditions B and C while answering N, A, P, D and E normally.

## What is deliberately not collected, and why

- **Further factorial orders for `x-ai/grok-4.3` and `moonshotai/kimi-k2.5`.** Neither refuses
  in any factorial cell; the factorial measures refusal, so more orders cannot change a verdict.
- **Further factorial orders for `google/gemini-3.7-flash`.** It refuses every sheet under every
  condition (18 of 18 in each of the four main conditions); more orders can only add refusals.
- **Rung 2 for the two Geminis.** Both refused every sheet of that arm, which is its result, not
  a gap.

## Design

A separate run directory, `runs/2026-09-25-wave-completion/`. The wave is frozen as the refusal
panel, and appending to it would move every panel figure; this arm is declared OUT_OF_PANEL in
`refusal_table.py` and is read only by the analyses named below. Temperature 0.7, template T01,
budget 40,960 tokens, five draws per cell with distinct sampling seeds (`--seed-sweep`).

| model | cells | protocol | channel / pin | seeds | sheets |
|---|---|---|---|---|---:|
| `z-ai/glm-5.2` | B, C, E, F000–F111 | v1 (as-is numbering), shuffle seed 11 — as its other wave cells | OpenRouter, pinned `Z.AI` if it serves (smoke-tested first); otherwise one other named backend, declared in an amendment before the first arm call | 20260926–20260930 | 55 |
| `google/gemini-3.8-flash` | F000–F111 at shuffle seeds 22 and 33 | v2 (renumbered `1..32`) — as the three floor-bearing models' second and third orders | OpenRouter, pinned `Google` (its wave backend) | 20260953–20260957 per order | 80 |
| `hf.co/culturerevolt/gemma-4-12b-heretic-abliterated-GGUF:Q4_K_M` | B, C | v1, shuffle seed 11, reasoning off — as its other wave cells | local (ollama) | 20260926–20260930 | 10 |

**Declared differences from the cells these complete.** The three floor-bearing models' later
orders carry one seed (20260830) on every draw and no backend pin; this arm uses distinct seeds
and a pin, which is the study's current rule. glm-5.2's other cells carry one seed on every draw
as well. Neither difference is a condition the analyses contrast.

## Predictions

1. **glm-5.2** answers the factorial as the other non-Google models do: no refusals in any F
   cell, or refusals only in cells carrying *multiple sides* or *no personal position*.
2. **gemini-3.8-flash** at two further orders reproduces its first order's direction: refusal
   higher with *multiple sides* and with *no personal position*, not with *acknowledge
   uncertainty*.
3. **culturerevolt B and C**: no prediction. If the build again returns nothing, that is the
   result and is reported as a reproducible local failure, not re-tried.

## Analysis — fixed now

- **glm-5.2**: `refusal_table.py --factorial` over this run, reported beside the wave's table as
  the eighth model; B, C and E refusal reported per condition.
- **gemini-3.8-flash**: the factorial floor calibration of
  `PREREG-2026-09-25-factorial-floor-calibration.md`, unchanged, run on its three orders (the
  wave's order 11 and this arm's 22 and 33), giving it a between-order floor; its per-clause
  verdicts are reported under the same clearing rule as the other three.
- **culturerevolt**: B and C refusal and validity, reported per condition.
- Nothing here re-enters the panel, and no panel figure changes.

## What would make this uninteresting

glm-5.2 behaving like every other non-Google model and gemini-3.8-flash reproducing its first
order: the factorial's verdicts then stand on four floor-bearing models instead of three, and
the eighth model adds a row, not a finding.
