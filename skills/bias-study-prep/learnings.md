# bias-study-prep learnings

Heuristics accumulated from running the skill across study runs. Add an entry whenever you encounter a failure mode worth remembering.

## Initial entries (2026-05-25, skill creation)

- **Skill is canonical at `bias-study-release/skills/bias-study-prep/`** (github.com/gorrie/bias-study), which is TRACKED. The runtime path `~/.claude/skills/bias-study-prep/` is a Windows directory junction into it, not a separate copy.
  Corrected 2026-09-02: this used to claim `.claude/skills/` was canonical, and that path is gitignored — so the skill, its four scripts and its ten tests were versioned nowhere while a line in this file said otherwise. A public/internal pair also existed, and the internal copy was the one being tuned, so the published copy described a protocol retired on 2026-08-29. One tracked tree now, no pair.
- **Env var presence is checked, not validated.** `OPENROUTER_API_KEY` set to "test" passes the check. Vendor-specific auth failures surface during the actual study run.
- **build.py exit codes**: `0=READY`, `1=NEEDS FIX`, `2=FAILED`. The skill treats only `0` as clean; any other code blocks the study.
- **No vendor calls in prep.** The prep MUST NOT touch any vendor API — that would burn quota and risk tripping anti-abuse heuristics during what should be a deterministic local check.
