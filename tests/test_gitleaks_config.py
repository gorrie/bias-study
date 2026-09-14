"""The secret scanner must detect THIS project's secret.

WHY THIS FILE EXISTS
--------------------
Measured 2026-09-13: a decoy file containing a real-shaped OpenRouter key, an AWS
secret and a GitHub token was scanned with this repository's `.gitleaks.toml` AND
with gitleaks' defaults alone. Both reported "no leaks found", exit 0.

gitleaks' default ruleset carries no OpenRouter pattern. So the single credential
every collection in this repository depends on was the one credential the scanner
could not see -- while the pre-commit hook reported clean on every commit.

That is the same defect as a gate passing over an empty corpus: it reports clean
because it looked at nothing relevant.

These tests assert the CONFIG, not the binary, so they run anywhere. The
end-to-end check (run gitleaks against a decoy and require a finding) is in the
config's own comment block and should be run whenever the rules change.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, ".gitleaks.toml")


@pytest.fixture(scope="module")
def cfg():
    with open(CONFIG, encoding="utf-8") as fh:
        return fh.read()


def test_an_openrouter_rule_exists(cfg):
    assert "openrouter-api-key" in cfg, (
        "no OpenRouter rule. gitleaks' defaults have none, so without this the "
        "scanner cannot see the key this project actually uses.")


def test_the_rule_matches_a_real_shaped_key(cfg):
    """Pull the regex out of the config and run it against a decoy."""
    m = re.search(r"""regex\s*=\s*'''(sk-or-v1-[^']+)'''""", cfg)
    assert m, "could not find the strict OpenRouter regex in the config"
    pattern = re.compile(m.group(1))
    decoy = "sk-or-v1-" + "0123456789abcdef" * 4          # 64 hex
    assert pattern.search('OPENROUTER_API_KEY = "%s"' % decoy), (
        "the OpenRouter rule does not match a real-shaped key")


def test_placeholders_are_allowlisted(cfg):
    for placeholder in ("sk-or-v1-X+", "REPLACE_WITH_YOUR_OWN_KEY"):
        assert placeholder in cfg, (
            "%r is not allowlisted; the repo's own templates would trip the scanner"
            % placeholder)


def test_readme_and_developer_are_NOT_path_exempt_from_key_rules(cfg):
    """A path exemption on prose files is where a pasted key goes to hide.

    The earlier config allowlisted README.md, DEVELOPER.md and skills/*/SKILL.md
    by PATH, which are precisely the files a key gets pasted into by accident.
    Placeholders in them are handled by shape instead.
    """
    exempt_block = cfg.split("paths = [", 1)[1].split("]", 1)[0] if "paths = [" in cfg else ""
    for risky in ("README", "DEVELOPER", "SKILL"):
        assert risky not in exempt_block, (
            "%s is path-exempt from secret scanning; a real key pasted there would "
            "not be caught" % risky)


def test_the_hash_inventory_allowlist_is_shape_based_not_path_based(cfg):
    """Source-hash files are exempted by what the line looks like, not where it is."""
    assert "regexTarget = \"line\"" in cfg, (
        "the hash-inventory allowlist must target the LINE; the extracted secret is "
        "a bare digest and carries none of the shape that identifies it as a hash")
    assert re.search(r"\\\.py\"\\s\*:", cfg) or ".py" in cfg, (
        "the hash-inventory allowlist should key on a .py path mapped to a digest")


def test_config_does_not_mix_deprecated_and_current_allowlist_forms(cfg):
    """gitleaks refuses to load a config using both, and a config that will not
    load is a scanner that does not run."""
    has_singular = re.search(r"^\[allowlist\]", cfg, re.MULTILINE)
    has_plural = re.search(r"^\[\[allowlists\]\]", cfg, re.MULTILINE)
    assert not (has_singular and has_plural), (
        "[allowlist] cannot be used alongside [[allowlists]] -- gitleaks fails to "
        "load the config entirely, which reads as a passing scan in any pipeline "
        "that does not check the exit code")
