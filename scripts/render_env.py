#!/usr/bin/env python3
"""Składa plik .run.env dla docker compose z: .env + profiles/set-<SET>.env + models.yaml.

Profil wskazuje modele po id (LLM_MODEL, LLM2_MODEL, EMBED_MODEL), a ten
skrypt dopisuje repo i rewizję z manifestu (LLM_REPO, LLM_REVISION, ...),
żeby rewizja była zapisana tylko w jednym miejscu: models.yaml.

Zależności: python3 + python3-yaml z apt (instaluje je bootstrap.sh).
Użycie: python3 scripts/render_env.py c   -> zapisuje .run.env
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ROLES = ("LLM", "LLM2", "LLM3", "LLM4", "EMBED")


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Użycie: render_env.py <SET>  (np. c)")
    set_name = sys.argv[1]
    profile = ROOT / "profiles" / f"set-{set_name}.env"
    if not profile.exists():
        sys.exit(f"Brak profilu {profile.relative_to(ROOT)}")
    if not (ROOT / ".env").exists():
        sys.exit("Brak .env — skopiuj .env.example do .env i uzupełnij")

    models = {m["id"]: m for m in yaml.safe_load((ROOT / "models.yaml").read_text(encoding="utf-8"))["models"]}

    env = read_env(ROOT / ".env")
    env.update(read_env(profile))
    env["SPARK_SET"] = set_name

    for role in ROLES:
        model_id = env.get(f"{role}_MODEL")
        if not model_id:
            continue
        if model_id not in models:
            sys.exit(f"{profile.name}: {role}_MODEL={model_id} nie istnieje w models.yaml")
        m = models[model_id]
        env[f"{role}_REPO"] = m["repo"]
        env[f"{role}_REVISION"] = m["revision"]
        env.setdefault(f"{role}_NAME", model_id)

    out = ROOT / ".run.env"
    lines = ["# Wygenerowane przez scripts/render_env.py — nie edytuj ręcznie."]
    lines += [f"{k}={v}" for k, v in env.items()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.chmod(0o600)  # zawiera HF_TOKEN
    print(f"Zapisano {out.name} (zestaw {set_name}, profile compose: {env.get('COMPOSE_PROFILES', '-')})")


if __name__ == "__main__":
    main()
