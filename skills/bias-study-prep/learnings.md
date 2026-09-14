# bias-study-prep learnings

Heuristics accumulated from running the skill across study runs. Add an entry whenever you encounter a failure mode worth remembering.

## Initial entries (2026-05-25, skill creation)

- **Skill is canonical at `bias-study-release/skills/bias-study-prep/`** (github.com/gorrie/bias-study), which is TRACKED. The runtime path `~/.claude/skills/bias-study-prep/` is a Windows directory junction into it, not a separate copy.
  Corrected 2026-09-02: this used to claim `.claude/skills/` was canonical, and that path is gitignored — so the skill, its four scripts and its ten tests were versioned nowhere while a line in this file said otherwise. A public/internal pair also existed, and the internal copy was the one being tuned, so the published copy described a protocol retired on 2026-08-29. One tracked tree now, no pair.
- **Env var presence is checked, not validated.** `OPENROUTER_API_KEY` set to "test" passes the check. Vendor-specific auth failures surface during the actual study run.
- **build.py exit codes**: `0=READY`, `1=NEEDS FIX`, `2=FAILED`. The skill treats only `0` as clean; any other code blocks the study.
- **No vendor calls in prep.** The prep MUST NOT touch any vendor API — that would burn quota and risk tripping anti-abuse heuristics during what should be a deterministic local check.

## 2026-09-13 — the eight-way audit

Full list with receipts: `research/bias-study/LEARNINGS.md` in the working tree. The ones that
change what this skill does:

- **Run `collection_check.py <run>` before spending a single judge call.** It is
  `COLLECTION-STANDARD.md` §4 made executable. Against the May pipeline wave it returns three
  blockers — no `max_tokens` recorded, 16.7% of responses severed mid-sentence, truncation
  differential at 33.3% vs 0.0%. Run in May it would have stopped that collection before any
  scoring. It did not exist, so the wave was scored and published.
- **Smoke a cell and measure OUTPUT LENGTH, not the exit code.** The defect that cost four
  months was a token cap, and a cap only shows as a length. If the longest smoke response lands
  near the cap, the cap is your ruining parameter — and the next model is more verbose.
- **Never trust `finish_reason` through a proxy.** Ten responses severed mid-word all reported
  `"stop"`. Read the text.
- **A gate that examined nothing must exit non-zero.** Four gates in this repo passed over an
  empty corpus. Probe every check you rely on against an empty tree once, and keep the probe.
- **Check whether exclusion is differential before excluding.** Dropping truncated records
  removed 94.1% of one vendor class and 0.0% of another. Filtering moved the confound into the
  denominator instead of removing it.
- **Ask what already exists before commissioning a collection.** A $259 re-collection was
  proposed while `2026-09-05-recollect` already covered part of the damage. `splice_holes.py`
  answers "how much is still missing", which is the question that matters. It was 176 cells.
