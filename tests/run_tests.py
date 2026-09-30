"""Run the matcher against tests/cases.json and report pass/fail.

Usage:  python tests/run_tests.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from arabic import normalize  # noqa: E402
from matcher import Matcher, check  # noqa: E402

cases = json.loads((ROOT / "tests" / "cases.json").read_text(encoding="utf-8"))
t = time.time()
m = Matcher()
print(f"index loaded in {time.time() - t:.1f}s\n")

passed = 0
for c in cases:
    t = time.time()
    v, res, _ = check(m, c["text"])
    ok = v == c["expect"]
    top = res[0] if res else None
    if ok and top and c.get("ref_contains"):
        ok = normalize(c["ref_contains"]) in normalize(top.record["ref"])
    passed += ok
    mark = "PASS" if ok else "FAIL"
    detail = f"{top.score:.0f} {top.record['ref']}" if top else "-"
    print(f"{mark}  {c['name']}: expected {c['expect']}, got {v}  [{detail}]  {time.time() - t:.2f}s")

print(f"\n{passed}/{len(cases)} passed")
sys.exit(0 if passed == len(cases) else 1)
