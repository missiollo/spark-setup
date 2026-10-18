#!/usr/bin/env python3
"""Jeden przebieg oceny agenta: worktree ze stanu bazowego → opencode run → check.py → wiersz CSV.

Użycie:
  run.py --task tasks/t1-fix-tests --repo ~/Documents/Projects/openMinesweeper \\
         --model spark/qwen3.6-35b-a3b [--variant rules] [--metrics-url http://localhost:8000/metrics] \\
         [--rep 1] [--repeat 3]

Wynik: runs/<RRRRMMDD-HHMM>-<zadanie>-<model>-<wariant>-r<N>/ (opencode.jsonl, diff.patch, check.json,
run.json, review.md) i wiersz w results-<zadanie>.csv. Szczegóły: docs/agent-eval.md.
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
METRICS = {
    "gen_tokens": r'^vllm:generation_tokens_total\{[^}]*\}\s+([0-9.e+]+)',
    "prompt_tokens": r'^vllm:prompt_tokens_total\{[^}]*\}\s+([0-9.e+]+)',
    "truncated": r'^vllm:request_success_total\{[^}]*finished_reason="length"[^}]*\}\s+([0-9.e+]+)',
    "requests": r'^vllm:request_success_total\{[^}]*\}\s+([0-9.e+]+)',
}


def read_metrics(url):
    if not url:
        return None
    try:
        text = urllib.request.urlopen(url, timeout=5).read().decode()
    except OSError:
        return None
    return {k: sum(float(m) for m in re.findall(p, text, re.M)) for k, p in METRICS.items()}


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=check).stdout


def slug(s):
    return re.sub(r"[^a-z0-9.]+", "-", s.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--model", required=True, help="provider/model jak w opencode.json")
    ap.add_argument("--variant", default="bare", help="bare | rules (AGENTS.md z tasks/<t>/AGENTS.rules.md)")
    ap.add_argument("--metrics-url", default=None, help="vLLM /metrics (Ollama nie ma — pomijamy)")
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--repeat", type=int, default=3, help="powtórzenia testów w check.py")
    ap.add_argument("--keep", action="store_true", help="nie usuwaj worktree po przebiegu")
    a = ap.parse_args()

    task_dir = (HERE / a.task).resolve() if not Path(a.task).is_absolute() else Path(a.task)
    task = json.loads((task_dir / "task.json").read_text())
    repo = Path(a.repo).expanduser().resolve()
    prompt = (task_dir / "prompt.md").read_text()
    base = task["base_ref"]
    git(repo, "rev-parse", "--verify", base)

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    name = f"{stamp}-{task['id']}-{slug(a.model.split('/')[-1])}-{a.variant}-r{a.rep}"
    out = HERE / "runs" / name
    out.mkdir(parents=True)
    wt = Path("/tmp") / f"agent-eval-{name}"

    git(repo, "worktree", "add", "--detach", str(wt), base)
    if (repo / "node_modules").is_dir():
        (wt / "node_modules").symlink_to(repo / "node_modules")
    if a.variant == "rules":
        shutil.copy(task_dir / "AGENTS.rules.md", wt / "AGENTS.md")
        git(wt, "add", "AGENTS.md")
        git(wt, "-c", "user.name=agent-eval", "-c", "user.email=agent-eval@localhost",
            "commit", "-qm", "eval: add AGENTS.md (rules variant)")
    start_ref = git(wt, "rev-parse", "HEAD").strip()

    m0 = read_metrics(a.metrics_url)
    t0 = time.time()
    limit = task.get("time_limit_min", 60) * 60
    timed_out = False
    with open(out / "opencode.jsonl", "w") as log, open(out / "opencode.stderr", "w") as err:
        p = subprocess.Popen(
            ["opencode", "run", "--dir", str(wt), "--model", a.model, "--format", "json",
             "--title", name, "--auto", prompt],
            stdout=log, stderr=err, stdin=subprocess.DEVNULL)
        try:
            rc = p.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            timed_out = True
    duration = time.time() - t0
    m1 = read_metrics(a.metrics_url)
    usage = {k: m1[k] - m0[k] for k in m1} if (m0 and m1) else None

    (out / "diff.patch").write_text(git(wt, "diff", start_ref, "--", ".", ":!node_modules", check=False)
                                    + "".join(f"\n# untracked: {f}" for f in
                                              git(wt, "ls-files", "--others", "--exclude-standard",
                                                  check=False).splitlines()
                                              if not f.startswith(("node_modules", "test-results"))))
    subprocess.run([sys.executable, "-I", str(HERE / "check.py"), "--task", str(task_dir),
                    "--repo", str(wt), "--base", start_ref, "--repeat", str(a.repeat), "--out", str(out)])
    chk = json.loads((out / "check.json").read_text())

    oc_version = subprocess.run(["opencode", "--version"], capture_output=True, text=True).stdout.strip()
    meta = {
        "name": name, "task": task["id"], "model": a.model, "variant": a.variant, "rep": a.rep,
        "base_ref": base, "base_sha": git(repo, "rev-parse", base).strip(),
        "started_utc": datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(duration), "exit_code": rc, "timed_out": timed_out,
        "opencode": oc_version, "metrics_url": a.metrics_url, "usage": usage,
    }
    (out / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    review = HERE / "review-template.md"
    if review.exists():
        (out / "review.md").write_text(review.read_text().replace("{{name}}", name))

    row = {
        "name": name, "task": task["id"], "model": a.model, "variant": a.variant, "rep": a.rep,
        "started_utc": meta["started_utc"], "duration_s": meta["duration_s"], "timed_out": timed_out,
    }
    for s, v in chk["suites"].items():
        last = v["runs"][-1] or {}
        row[f"{s}_passed"] = last.get("passed")
        row[f"{s}_total"] = last.get("total")
        row[f"{s}_full_pass_runs"] = v["all_passed_runs"]
        row[f"{s}_flaky"] = len(v["flaky"])
        row[f"{s}_removed"] = v["tests_removed"]
    row.update({
        "files_changed": len(chk["changed_files"]), "logic_changed": len(chk["logic_changed"]),
        "skip_or_only": len(chk["skip_or_only"]), "leftovers": len(chk["leftover_files"]),
        "gen_tokens": usage and int(usage["gen_tokens"]), "prompt_tokens": usage and int(usage["prompt_tokens"]),
        "truncated": usage and int(usage["truncated"]),
        "review_score": "", "interventions": "",
    })
    csv_path = HERE / f"results-{task['id']}.csv"
    new = not csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)

    if a.keep:
        print(f"worktree zachowany: {wt}")
    else:
        git(repo, "worktree", "remove", "--force", str(wt), check=False)
    print(f"przebieg: {out}")


if __name__ == "__main__":
    sys.exit(main())
