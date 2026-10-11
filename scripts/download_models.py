#!/usr/bin/env python3
"""Pobiera modele z models.yaml do HF_HOME (domyślnie /data/hf).

Uruchamiane przez `make models` / `make pin` w kontenerze python (nic nie
instalujemy przez pip na hoście). Można też uruchomić ręcznie, jeśli
huggingface_hub i pyyaml są dostępne.

  download_models.py --set c          # modele z zestawu c
  download_models.py --id bge-m3      # pojedynczy model
  download_models.py --all            # wszystko z manifestu
  download_models.py --set c --pin    # tylko wypisz aktualne SHA (nic nie pobiera)
  download_models.py --list
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from huggingface_hub import HfApi, snapshot_download

MANIFEST = Path(__file__).resolve().parent.parent / "models.yaml"


def load_models() -> list[dict]:
    with MANIFEST.open(encoding="utf-8") as f:
        return yaml.safe_load(f)["models"]


def select(models: list[dict], args: argparse.Namespace) -> list[dict]:
    if args.all:
        return models
    if args.id:
        chosen = [m for m in models if m["id"] in args.id]
        missing = set(args.id) - {m["id"] for m in chosen}
        if missing:
            sys.exit(f"Nieznane id w models.yaml: {', '.join(sorted(missing))}")
        return chosen
    if args.set:
        chosen = [m for m in models if args.set in m.get("sets", [])]
        if not chosen:
            sys.exit(f"Żaden model nie należy do zestawu '{args.set}'")
        return chosen
    sys.exit("Podaj --set, --id albo --all (lub --list)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set")
    p.add_argument("--id", nargs="+")
    p.add_argument("--all", action="store_true")
    p.add_argument("--pin", action="store_true", help="wypisz SHA dla revision, nic nie pobieraj")
    p.add_argument("--list", action="store_true")
    args = p.parse_args()

    models = load_models()

    if args.list:
        for m in models:
            print(f"{m['id']:<20} {m['repo']:<36} rev={m['revision']:<10} ~{m.get('size_gb', '?')} GB  sets={m.get('sets', [])}")
        return

    chosen = select(models, args)
    token = os.environ.get("HF_TOKEN") or None
    api = HfApi(token=token)

    if args.pin:
        print("# Wklej do models.yaml (revision:) dla przypięcia wersji:")
        for m in chosen:
            sha = api.model_info(m["repo"], revision=m["revision"]).sha
            print(f"{m['id']:<20} {m['repo']:<36} {m['revision']} -> {sha}")
        return

    total = sum(float(m.get("size_gb", 0)) for m in chosen)
    print(f"HF_HOME={os.environ.get('HF_HOME', '~/.cache/huggingface')}")
    print(f"Do pobrania (orientacyjnie): {total:.0f} GB, modele: {', '.join(m['id'] for m in chosen)}\n")

    for m in chosen:
        if m["revision"] == "main":
            print(f"[uwaga] {m['id']}: revision=main (nieprzypięte). Po teście uruchom `make pin`.")
        print(f"==> {m['id']}  ({m['repo']}@{m['revision']})", flush=True)
        path = snapshot_download(
            repo_id=m["repo"],
            revision=m["revision"],
            token=token,
            ignore_patterns=m.get("ignore"),
        )
        sha = Path(path).name
        print(f"    OK: {path}\n    sha: {sha}\n", flush=True)

    print("Gotowe.")


if __name__ == "__main__":
    main()
