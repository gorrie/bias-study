#!/usr/bin/env python3
"""Names a script uses and never binds -- the NameError that waits for a rare path.

WHY THIS EXISTS
---------------
`recollect_at_cap.py` used `LEGACY_SEED` when writing its manifest and imported
`run_roots` only. Python does not care until the line runs, and that line runs
LAST -- after every API call has been made, paid for, and written to disk. So the
run produced a complete set of records, crashed, and left no manifest.

That is the worst possible shape for a failure in this project: the expensive
part succeeded, the cheap part died, and what was lost (provenance) is the thing
whose absence surfaces weeks later in a different tool, as a finding on a run
nobody remembers collecting. It went unnoticed for a further reason worth
recording -- `repair_recollect_provenance.py --manifests` had been backfilling
the missing manifests, so the symptom was being cleaned up faster than the cause
could be seen.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT
-------------------------------------------------
For each file: every name READ anywhere, minus every name BOUND anywhere in that
file, minus builtins. If a name is bound anywhere at all -- any scope, any branch
-- it is not reported.

That rule is deliberately far weaker than a real scope analysis, and the weakness
is the point. A checker that reasons about scopes finds more bugs and also finds
false positives, and a linter that cries wolf in this repository gets switched
off wholesale -- which is how `validate_runs.py` came to have 44 live findings
wired into no gate. This one cannot produce a false positive from a scope
subtlety, because it never reasons about scope. It catches exactly the class that
bit us: a global that is used and never imported.

    python scripts/check_undefined_names.py
    python scripts/check_undefined_names.py --check     # exit 1 on any finding
"""
from __future__ import annotations

import argparse
import ast
import builtins
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: Names that are legitimately unbound in a file: injected by the runtime, or
#: bound by machinery this checker does not model. Keep this list SHORT and give
#: every entry a reason -- it is the only place a real finding can hide.
ALLOWED = {
    "__file__", "__name__", "__doc__", "__package__", "__spec__", "__loader__",
    "__builtins__", "__debug__",
    # pytest injects these into conftest-style helpers.
    "__tracebackhide__",
}


def _bound_names(tree):
    """Every name this module binds, anywhere, by any mechanism."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            out.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                               ast.Lambda)):
            # ast.Lambda has args and no name, and leaving it out of this branch
            # reported every `key=lambda x: ...` parameter in the repo as
            # undefined -- 24 of the first run's 29 findings. A checker whose
            # output is mostly noise is one nobody reads, which is the failure it
            # was written to prevent.
            if not isinstance(node, ast.Lambda):
                out.add(node.name)
            args = getattr(node, "args", None)
            if args is not None:
                for a in (list(args.args) + list(args.posonlyargs)
                          + list(args.kwonlyargs)):
                    out.add(a.arg)
                for a in (args.vararg, args.kwarg):
                    if a is not None:
                        out.add(a.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    # A star-import binds names this checker cannot enumerate, so
                    # the file is not checkable and is skipped by the caller.
                    out.add("*")
                    continue
                out.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            out.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            out.add(node.name)
        elif isinstance(node, (ast.comprehension,)):
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    out.add(n.id)
        elif isinstance(node, ast.MatchAs) and node.name:
            out.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name:
            out.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            out.add(node.rest)
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for n in ast.walk(node.optional_vars):
                if isinstance(n, ast.Name):
                    out.add(n.id)
    return out


def check_source(src, path="<string>"):
    """Return [(lineno, name)] for names read but never bound in this source."""
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as exc:
        return [(exc.lineno or 0, "SyntaxError: %s" % exc.msg)]
    bound = _bound_names(tree)
    if "*" in bound:
        return []  # star-import: not checkable, and saying so beats guessing
    known = bound | set(dir(builtins)) | ALLOWED
    seen = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in known and node.id not in seen:
                seen[node.id] = node.lineno
    return sorted((line, name) for name, line in seen.items())


def scan(dirs=("scripts", "tests")):
    findings = []
    n_files = 0
    for d in dirs:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            with io.open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            n_files += 1
            for line, bad in check_source(src, path):
                findings.append({"file": os.path.join(d, name),
                                 "line": line, "name": bad})
    return n_files, findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 on any finding")
    args = ap.parse_args(argv)

    n_files, findings = scan()
    if not n_files:
        print("CHECKED NOTHING -- no Python files found. This is not a pass.",
              file=sys.stderr)
        return 1

    print("undefined-name scan: %d file(s), %d finding(s)" % (n_files, len(findings)))
    for f in findings:
        print("  %s:%d  %s" % (f["file"], f["line"], f["name"]))
    if findings:
        print("\nEach of these is a NameError waiting for the line to run. The one that"
              "\nprompted this check sat at the END of a collector, so the run made every"
              "\nAPI call, wrote every record, and then died before its manifest.")
    return 1 if (args.check and findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
