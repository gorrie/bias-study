"""`score.py --skip-classifier` must run with no network library installed.

WHY THIS FILE EXISTS
--------------------
The README tells a replicator without an API key to run
`score.py --skip-classifier`. That path uses the heuristic scorer and makes no
network call whatsoever -- but `import requests` sat at module level, so it died
on `ModuleNotFoundError` before reaching a single record.

The one documented route into this study for someone who has not installed our
dependencies was the route that could not run. `check_no_key_repro.py` is the
gate that exercises the README's own instructions with no credentials present,
and it caught this; nothing else would have, because everyone working on the
study has requests installed.
"""
import importlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)


def test_module_level_import_of_requests_is_gone():
    import inspect
    import score
    src = inspect.getsource(score)
    header = src.split("def ", 1)[0]
    body_lines = [ln for ln in header.split("\n")
                  if not ln.strip().startswith("#")]
    assert "import requests" not in "\n".join(body_lines), (
        "requests is imported at module level again; --skip-classifier will die "
        "for anyone who has not installed it")


def test_requests_is_imported_where_it_is_used():
    import inspect
    import score
    src = inspect.getsource(score.call_judge)
    assert "import requests" in src, (
        "call_judge must import requests itself, or the judge path breaks")


#: Blocks `import requests` in a subprocess, using the CURRENT finder protocol.
#: The first version of this used find_module/load_module, removed in Python 3.12,
#: so it blocked nothing and the test below passed without testing anything. The
#: negative control caught it, which is the entire reason it is here.
BLOCKER = (
    "import sys\n"
    "from importlib.abc import MetaPathFinder\n"
    "class Blocker(MetaPathFinder):\n"
    "    def find_spec(self, name, path=None, target=None):\n"
    "        if name == 'requests' or name.startswith('requests.'):\n"
    "            raise ImportError('requests is blocked for this test')\n"
    "        return None\n"
    "sys.meta_path.insert(0, Blocker())\n"
)


def test_score_imports_with_requests_unavailable():
    """The decisive test: import the module where requests cannot load."""
    code = BLOCKER + (
        "sys.path.insert(0, %r)\n"
        "import score\n"
        "print('OK')\n"
    ) % SCRIPTS
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert p.returncode == 0, (
        "score.py cannot be imported without requests:\n%s" % (p.stderr[-1500:],))
    assert "OK" in p.stdout


def test_the_blocker_really_blocks():
    """Negative control. Without this the test above proves nothing."""
    p = subprocess.run([sys.executable, "-c", BLOCKER + "import requests\n"],
                       capture_output=True, text=True)
    assert p.returncode != 0, "the import blocker does not block"
    assert "blocked for this test" in p.stderr
