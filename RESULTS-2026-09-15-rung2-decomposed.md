# Rung 2 is a system prompt, on one model. Decomposed.

> **HISTORICAL — the retired design's pipeline rung.** Judge-scored cell means on the
> ten-question free-text instrument, collected through the proxy. The present study re-collected
> rung 2 on the 32-item battery through its own transport; that result is in
> [`PAPER-below-the-floor.md`](PAPER-below-the-floor.md). Kept as the companion to
> [`RESULTS-2026-09-14-rung2-transform-audit.md`](RESULTS-2026-09-14-rung2-transform-audit.md).

**2026-09-15.** [`data/2026-09-15-g0dm0d3-decomposition`](data/2026-09-15-g0dm0d3-decomposition/) — four conditions, two models, ten
questions, five samples, **all collected in one sitting** so no contrast crosses a day.

```bash
python scripts/pipeline_decomposition.py
python scripts/pipeline_decomposition.py --selftest   # planted answers, no corpus
```

---

## The question this settles

After the 2026-09-14 audit, rung 2's only surviving effect belonged to `godmode` and `autotune`
together — Parseltongue applies nothing to this instrument and STM's edit is a median of 16
characters. No arm had ever run one without the other, so the honest sentence was *"a system
prompt plus a sampling change moved Grok and not Opus"*, which cannot say whether the models are
responding to an **instruction** or to a **temperature**. Those are different findings about
different things, and only one of them is about alignment.

| condition | what it applies |
|---|---|
| `B-Proxy` | nothing — plain condition B through the proxy, every transform off. **The baseline.** |
| `B-Godmode` | a system prompt (`GODMODE_SYSTEM_PROMPT` + `DEPTH_DIRECTIVE`), plus temperature +0.1, presence +0.15, frequency +0.1 |
| `B-Autotune` | sampling parameters replaced outright — temperature 0.825 against the baseline's 0.7, top_p 0.9, top_k 50 |
| `B-Layered` | both, plus STM and the inert Parseltongue |

Verified before a single judge call: godmode fired on 99 of 100, autotune on 99 of 100, and the
control received nothing. `collection_check` ACCEPTED; 3 of 400 calls lost to proxy read-timeouts,
one in each of three Grok conditions, so nothing systematic.

## The result

Cell means, eligible records:

| model | B-Proxy | B-Godmode | B-Autotune | B-Layered |
|---|---:|---:|---:|---:|
| claude-opus-4.7 | 3.48 | 3.50 | 3.44 | 3.44 |
| grok-4.3 | 3.63 | **4.10** | 3.55 | **4.04** |

Paired per question against the same-sitting baseline:

| model | contrast | effect | 95% interval | |
|---|---|---:|---|---|
| **grok-4.3** | **B-Godmode minus B-Proxy** | **+0.45** | [+0.10, +0.78] | excludes 0 |
| grok-4.3 | B-Autotune minus B-Proxy | −0.08 | [−0.26, +0.09] | |
| **grok-4.3** | **B-Layered minus B-Proxy** | **+0.44** | [+0.07, +0.79] | excludes 0 |
| claude-opus-4.7 | B-Godmode minus B-Proxy | +0.02 | [−0.26, +0.28] | |
| claude-opus-4.7 | B-Autotune minus B-Proxy | −0.04 | [−0.12, +0.04] | |
| claude-opus-4.7 | B-Layered minus B-Proxy | −0.04 | [−0.34, +0.22] | |

**Additivity holds on both models** — residuals −0.02 [−0.18, +0.14] and +0.06 [−0.09, +0.23] —
so the stack is the sum of its parts and the single-arm numbers generalise to it.

### It is the instruction, not the temperature

`B-Layered` (+0.44) is `B-Godmode` (+0.45) to within a rounding error, and `B-Autotune` is
nothing. The whole of rung 2's effect on Grok is the **godmode system prompt**.

The sampling hypothesis gets the *better-powered* test of the two and comes back null, which is
what makes this more than a two-arm coincidence. `autotune` is the **larger** parameter
perturbation — temperature 0.825 against 0.7, plus top_p 0.9 and top_k 50 — while godmode's
bundled boost is a quarter of that, +0.1 on temperature. A bigger sampling change produced no
movement; a smaller one carrying an instruction produced +0.45. If the effect were sampling, the
arms would be the other way round.

The residual caveat, which no flag can remove: `applyGodmodeBoost` runs whenever godmode is set,
so "system prompt with no parameter change" is not reachable through this API. The comparison
above is the strongest available and it is not a clean isolation.

---

## What this costs: "opposite directions" does not survive a clean baseline

This has to be stated plainly, because it corrects the one rung-2 finding that had walked
through every previous correction untouched — including in this session's own commit messages.

The published survivor was `B-Layered minus B-STM`: **Opus −0.31 [−0.64, −0.01], Grok +0.48
[+0.26, +0.70]** — two models moving in *opposite directions* under the same intervention. It was
robust to the token-budget confound and to the proxy-path confound precisely because it is
within-arm and never reads a baseline run.

But its reference arm is `B-STM`, and **B-STM is not an untreated control.** It is the arm whose
scored text the proxy edits, on 45 of 60 Opus records. Measured here against an arm that received
genuinely nothing, Opus reads **−0.04 [−0.34, +0.22]** — flat, like every other Opus contrast in
this run.

**Opus does not move under any ingredient of rung 2.** Its four cell means span 3.44 to 3.50.
The negative half of "opposite directions" was a contrast against a treated reference, not a
direction.

So the corrected finding is narrower and one-sided:

> **A forceful system prompt moves Grok 4.3 by about half a point on this rubric and does not
> move Claude Opus 4.7 at all.** The sampling change moves neither. Obfuscation was never applied.
> Hedge-stripping edits the answer rather than the model and moves neither.

That is still a real model-difference finding, and it is smaller than what rung 2 has been
carrying. It is also the first version of it measured against a baseline that received nothing,
in the same sitting, with every transform verified to have fired.

---

## Limitations, stated

- **Ten questions, one instrument, two models.** Everything here is one arm of one study.
- **Ragged replicate depth [3, 4, 5]** — 400 collected, 393 classified, 3 lost to timeouts and
  the rest to judges declining. Reported rather than smoothed; the estimator prints it.
- **n is questions, not draws.** Replicates are averaged within cell before differencing, so
  every interval above is a bootstrap over 10 paired questions. That is the binding limit on
  precision and no amount of sampling fixes it.
- **The godmode system prompt is not isolated from its own parameter boost**, as above.
- **This says nothing about a ceiling.** Locating where added force stops helping needs more
  than three points on one axis, at any sample size, and nothing here attempts it.
