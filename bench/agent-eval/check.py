#!/usr/bin/env python3
"""Sprawdzenie wyniku przebiegu agenta: testy (N powtórzeń), zakres zmian, naruszenia zasad.

Użycie:
  check.py --task tasks/t1-fix-tests --repo <katalog> [--base <ref>] [--repeat 3] [--out <katalog>]

Bez --base porównuje z HEAD (przebieg zerowy na stanie wyjściowym).
Wynik: <out>/check.json i podsumowanie na stdout. Tylko biblioteka standardowa.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN = re.compile(r"\b(?:test|it|describe)\.(?:skip|only|fixme)\(|\bx(?:it|test|describe)\(")


def sh(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def run_jest(repo, out_file):
    sh(f"npx jest --json --outputFile={out_file}", repo)
    try:
        data = json.loads(Path(out_file).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    tests = {}
    for suite in data.get("testResults", []):
        for t in suite.get("assertionResults", []):
            tests[t["fullName"]] = t["status"]
    return {
        "total": data.get("numTotalTests", 0),
        "passed": data.get("numPassedTests", 0),
        "failed": data.get("numFailedTests", 0),
        "skipped": data.get("numPendingTests", 0) + data.get("numTodoTests", 0),
        "tests": tests,
    }


def walk_pw(suite, prefix, tests):
    title = suite.get("title", "")
    path = f"{prefix} › {title}" if prefix and title else (title or prefix)
    for spec in suite.get("specs", []):
        status = "passed"
        for t in spec.get("tests", []):
            res = t.get("results", [])
            last = res[-1]["status"] if res else "skipped"
            if t.get("status") == "skipped" or last == "skipped":
                status = "skipped"
            elif last != "passed":
                status = "failed"
        tests[f"{path} › {spec['title']}"] = status
    for s in suite.get("suites", []):
        walk_pw(s, path, tests)


def run_playwright(repo, out_file):
    _, stdout, _ = sh("npx playwright test --reporter=json", repo)
    Path(out_file).write_text(stdout)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    tests = {}
    for s in data.get("suites", []):
        walk_pw(s, "", tests)
    vals = list(tests.values())
    return {
        "total": len(vals),
        "passed": vals.count("passed"),
        "failed": vals.count("failed"),
        "skipped": vals.count("skipped"),
        "tests": tests,
    }


RUNNERS = {"jest": run_jest, "playwright": run_playwright}


def changed_files(repo, base):
    _, numstat, _ = sh(f"git diff --numstat {base}", repo)
    files = {}
    for line in numstat.splitlines():
        added, deleted, name = line.split("\t", 2)
        files[name] = {"added": added, "deleted": deleted}
    _, untracked, _ = sh("git ls-files --others --exclude-standard", repo)
    for name in untracked.splitlines():
        files.setdefault(name, {"added": "new", "deleted": "0"})
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", default="HEAD")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    task = json.loads((Path(a.task) / "task.json").read_text())
    repo = Path(a.repo).resolve()
    out = Path(a.out or ".").resolve()
    out.mkdir(parents=True, exist_ok=True)

    suites = {}
    for name in task["test_suites"]:
        runs = []
        for i in range(1, a.repeat + 1):
            r = RUNNERS[name](repo, out / f"{name}-{i}.json")
            runs.append(r)
        ok = [r for r in runs if r]
        names = sorted({t for r in ok for t in r["tests"]})
        always_fail = [t for t in names if all(r["tests"].get(t) == "failed" for r in ok)]
        flaky = [t for t in names
                 if len({r["tests"].get(t) for r in ok} - {"skipped"}) > 1]
        base_total = task.get("baseline_total", {}).get(name)
        suites[name] = {
            "runs": [{k: v for k, v in r.items() if k != "tests"} if r else None for r in runs],
            "all_passed_runs": sum(1 for r in ok if r["failed"] == 0 and r["total"] > 0),
            "always_failing": always_fail,
            "flaky": flaky,
            "baseline_total": base_total,
            "tests_removed": (base_total - ok[-1]["total"]) if (ok and base_total) else None,
        }

    ignore = [re.compile(p) for p in task.get("ignore", [])]
    files = {f: v for f, v in changed_files(repo, a.base).items()
             if not any(r.match(f) for r in ignore)}
    logic_changed = [f for f in files if any(re.fullmatch(p, f) for p in task.get("logic_files", []))]
    test_files = [f for f in files if any(re.fullmatch(p, f) for p in task.get("test_files", []))]
    forbidden_hits = []
    for f in test_files:
        p = repo / f
        if p.is_file():
            for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if FORBIDDEN.search(line):
                    forbidden_hits.append(f"{f}:{n}: {line.strip()}")
    leftovers = [f for f in files if re.search(r"\.(bak|orig|tmp)$", f)]

    result = {
        "task": task["id"],
        "repo": str(repo),
        "base": a.base,
        "repeat": a.repeat,
        "suites": suites,
        "changed_files": files,
        "logic_changed": logic_changed,
        "skip_or_only": forbidden_hits,
        "leftover_files": leftovers,
    }
    (out / "check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))

    for name, s in suites.items():
        last = s["runs"][-1] or {}
        print(f"{name}: {last.get('passed', '?')}/{last.get('total', '?')} zaliczone (ostatni przebieg), "
              f"pełne zaliczenie {s['all_passed_runs']}/{a.repeat}, "
              f"zawsze padają {len(s['always_failing'])}, niestabilne {len(s['flaky'])}, "
              f"usunięte testy {s['tests_removed']}")
    print(f"zmienione pliki: {len(files)}, logika gry: {logic_changed or '-'}, "
          f"skip/only: {len(forbidden_hits)}, pozostałości: {leftovers or '-'}")
    print(f"szczegóły: {out / 'check.json'}")


if __name__ == "__main__":
    sys.exit(main())
