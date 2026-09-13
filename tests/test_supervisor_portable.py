"""The dose supervisor must be startable on the box it was written for: Windows."""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import supervised_dose_series as S


def test_process_group_kwargs_are_valid_for_this_platform():
    """It used preexec_fn=os.setsid, which raises ValueError on Windows -- so the script died
    at its first Popen on the 4090, the only machine that runs the work it supervises."""
    kw = S._new_process_group()
    assert kw, "must request a new process group on both platforms"
    if os.name == "nt":
        assert "creationflags" in kw and "preexec_fn" not in kw
    else:
        assert kw == {"start_new_session": True}


def test_the_kwargs_actually_start_a_process():
    """Asserting the dict shape is not enough -- Popen is what rejects preexec_fn."""
    p = subprocess.Popen([sys.executable, "-c", "pass"], **S._new_process_group())
    p.wait(timeout=30)
    assert p.returncode == 0


def test_kill_tree_terminates_a_live_child():
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                         **S._new_process_group())
    S._kill_tree(p)
    p.wait(timeout=30)
    assert p.poll() is not None, "the child survived _kill_tree"


def test_no_posix_only_symbol_is_referenced_unguarded():
    """signal.SIGKILL does not exist on Windows; referencing it outside an os.name guard is an
    AttributeError at the moment the supervisor is trying to recover from a hang."""
    src = (Path(S.__file__)).read_text(encoding="utf-8")
    for line in src.splitlines():
        if "SIGKILL" in line and not line.strip().startswith("#"):
            assert "os.name" in src.split(line)[0][-400:], \
                "SIGKILL referenced outside the POSIX branch: " + line.strip()
