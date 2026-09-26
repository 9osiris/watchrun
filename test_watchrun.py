#!/usr/bin/env python3
# tests for watchrun. run with: python3 test_watchrun.py

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import watchrun

PY = sys.executable

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"ok - {name}")
    else:
        failed += 1
        print(f"FAIL - {name}")


# unit: hidden detection
check("is_hidden dotfile", watchrun.is_hidden(".foo/bar"))
check("is_hidden normal", not watchrun.is_hidden("src/main.py"))

# unit: ignorer matches full paths and tails
ign = watchrun.make_ignorer(["*.log", "build/*"])
check("ignorer matches ext", ign("src/debug.log"))
check("ignorer matches dir glob", ign("/x/build/out.o"))
check("ignorer passes normal", not ign("src/main.py"))

# unit: snapshot walks dirs, skips hidden by default
d = Path(tempfile.mkdtemp())
(d / "a.py").write_text("a")
(d / ".h").write_text("h")
sub = d / "sub"
sub.mkdir()
(sub / "b.py").write_text("b")
snap = watchrun.snapshot([str(d)], False, watchrun.make_ignorer([]))
check("snapshot sees files",
      any(p.endswith("a.py") for p in snap)
      and any(p.endswith("b.py") for p in snap))
check("snapshot skips hidden by default",
      not any(".h" in p for p in snap))
snap = watchrun.snapshot([str(d)], True, watchrun.make_ignorer([]))
check("snapshot --all includes hidden",
      any(p.endswith(".h") for p in snap))
snap = watchrun.snapshot([str(d)], False, watchrun.make_ignorer(["*.py"]))
check("snapshot honors ignore globs", snap == {})

# unit: run returns the command's exit code
rc = watchrun.run([PY, "-c", "import sys; sys.exit(4)"], False)
check("run returns exit code", rc == 4)
try:
    watchrun.run(["definitely-not-a-real-cmd-xyz"], False)
    check("run missing command exits 127", False)
except SystemExit as e:
    check("run missing command exits 127", e.code == 127)


def run_cli(*args, cwd=None, timeout=15):
    return subprocess.run([PY, str(HERE / "watchrun.py"), *args],
                          capture_output=True, text=True, cwd=cwd,
                          timeout=timeout)


# cli: --once runs once and exits instead of watching
wd = Path(tempfile.mkdtemp())
r = run_cli("--once", str(wd), "--", PY, "-c", "print('ran-once')",
            timeout=10)
check("--once exits 0", r.returncode == 0)
check("--once ran the command", "ran-once" in r.stdout)
check("--once ran exactly once", r.stdout.count("$ ") == 1)

# cli: --once passes the exit code through
r = run_cli("--once", str(wd), "--", PY, "-c", "import sys; sys.exit(7)",
            timeout=10)
check("--once exit code passes through", r.returncode == 7)

# cli: --fail-fast stops on the first failing run
r = run_cli("--fail-fast", "--interval", "0.2", str(wd), "--",
            PY, "-c", "import sys; sys.exit(3)", timeout=10)
check("--fail-fast exits with the failing code", r.returncode == 3)
check("--fail-fast ran once, not forever", r.stdout.count("$ ") == 1)

# cli: without --fail-fast a failing command keeps watching
p = subprocess.Popen([PY, str(HERE / "watchrun.py"), "--interval", "0.2",
                      str(wd), "--", PY, "-c", "import sys; sys.exit(3)"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(1.5)
alive = p.poll() is None
p.terminate()
p.wait(timeout=10)
check("failing run without --fail-fast keeps watching", alive)

# cli: --fail-fast keeps watching while runs succeed, reruns on change
p = subprocess.Popen([PY, str(HERE / "watchrun.py"), "--interval", "0.2",
                      "--debounce", "0.2", "--fail-fast",
                      str(wd), "--", PY, "-c", "print('tick')"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(1.0)
check("--fail-fast alive while runs succeed", p.poll() is None)
(wd / "trigger.txt").write_text("x")
time.sleep(2.0)
check("--fail-fast still alive after successful rerun", p.poll() is None)
p.terminate()
out, _ = p.communicate(timeout=10)
check("change triggered a rerun", out.count("$ ") >= 2)

# cli: --fail-fast stops after a failing rerun
wd2 = Path(tempfile.mkdtemp())
counter = Path(tempfile.mkdtemp()) / "count.txt"  # outside the watched dir,
# so only trigger.txt causes reruns
script = ("import sys, pathlib; p = pathlib.Path(sys.argv[1]); "
          "n = int(p.read_text()) if p.exists() else 0; "
          "p.write_text(str(n + 1)); sys.exit(1 if n >= 1 else 0)")
p = subprocess.Popen([PY, str(HERE / "watchrun.py"), "--interval", "0.2",
                      "--debounce", "0.2", "--fail-fast",
                      str(wd2), "--", PY, "-c", script, str(counter)],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(1.0)
check("first run succeeded, still watching", p.poll() is None)
(wd2 / "trigger.txt").write_text("x")
try:
    rc = p.wait(timeout=10)
    check("--fail-fast exits with the failing rerun code", rc == 1)
except subprocess.TimeoutExpired:
    p.terminate()
    p.wait(timeout=10)
    check("--fail-fast exits with the failing rerun code", False)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
