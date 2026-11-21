#!/usr/bin/env python3
"""R09-T012 wrapper: runs tools/course_checks/r09-t012.py and verifies its result."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOL = ROOT / "tools" / "course_checks" / "r09-t012.py"

p = subprocess.run([sys.executable, str(TOOL), "--evidence-dir", str(HERE)], cwd=ROOT)
print(f"child exit code: {p.returncode}")
if p.returncode != 0:
    print("FAIL: course check exited non-zero")
    sys.exit(1)
res = json.loads((HERE / "results.json").read_text())
executed = res.get("executed_cases", 0)
print(f"Executed cases: {executed}")
if executed == 0:
    print("FAIL: zero-test run")
    sys.exit(1)
print("Wrapper: all checks passed")
