#!/usr/bin/env python3
"""Pomiar TTFT i prędkości generowania dla API zgodnego z OpenAI (vLLM).

Tylko biblioteka standardowa — działa na Sparku i na Macu (przez tunel).

Dla każdej długości promptu wykonuje dwa zapytania:
  cold — unikalny początek promptu, więc prefix cache nie pomaga (pełny prefill),
  warm — identyczny prompt drugi raz (prefill z prefix cache).

  python3 bench/run_bench.py                       # domyślnie localhost:8000, model z /v1/models
  python3 bench/run_bench.py --lengths 1000 4000 16000 --max-tokens 256
  python3 bench/run_bench.py --thinking            # z trybem rozumowania (Qwen)

Wyniki: tabela na ekranie + JSON w --out (do commitowania i porównań między platformami).
Liczby wpisuj do symulatora (efektywne TFLOPS ≈ 2 × aktywne_param × tokeny / czas_prefillu).
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

FILLER = (
    "REQ-{i:04d} | Wymaganie {i} | pakiet: Kontrola graniczna | status: zatwierdzone | "
    "opis: System rejestruje zdarzenie kontroli dokumentu i zapisuje wynik weryfikacji. | realizuje: CMP-{c:03d}\n"
)
QUESTION = "\nKtóre z powyższych wymagań nie mają komponentu realizującego? Odpowiedz krótko."


def http_json(url: str, payload: dict | None = None, timeout: float = 30):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def build_prompt(approx_tokens: int, nonce: str) -> str:
    # ~40 tokenów na linię w typowym tokenizerze; dokładną liczbę zwraca serwer (usage).
    lines = [f"[run {nonce}]\n"]
    for i in range(max(1, approx_tokens // 40)):
        lines.append(FILLER.format(i=i, c=(i * 7) % 97))
    return "".join(lines) + QUESTION


def run_one(base: str, model: str, prompt: str, max_tokens: int, thinking: bool, effort_none: bool = False) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": thinking},
    }
    # Ollama ignoruje chat_template_kwargs; rozumowanie wyłącza tam tylko reasoning_effort="none"
    if effort_none and not thinking:
        payload["reasoning_effort"] = "none"
    t0 = time.perf_counter()
    t_first = None
    usage = {}
    with http_json(f"{base}/chat/completions", payload, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            chunk = json.loads(body)
            if chunk.get("usage"):
                usage = chunk["usage"]
            for ch in chunk.get("choices", []):
                delta = ch.get("delta", {})
                if t_first is None and (delta.get("content") or delta.get("reasoning_content") or delta.get("reasoning")):
                    t_first = time.perf_counter()
    t_end = time.perf_counter()
    t_first = t_first or t_end
    out_tok = usage.get("completion_tokens", 0)
    decode_s = t_end - t_first
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": out_tok,
        "ttft_s": round(t_first - t0, 3),
        "decode_s": round(decode_s, 3),
        "decode_tok_s": round((out_tok - 1) / decode_s, 1) if out_tok > 1 and decode_s > 0 else None,
        "total_s": round(t_end - t0, 3),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--model", help="domyślnie pierwszy z /v1/models")
    p.add_argument("--lengths", type=int, nargs="+", default=[1000, 4000, 16000])
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--thinking", action="store_true", help="włącz tryb rozumowania (domyślnie wyłączony)")
    p.add_argument("--reasoning-effort-none", action="store_true",
                   help="bez --thinking wysyła też reasoning_effort=none (Ollama); vLLM tego nie potrzebuje")
    p.add_argument("--platform", default="dgx-spark", help="etykieta platformy w wynikach")
    p.add_argument("--out", default="bench/results")
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    model = args.model or json.load(http_json(f"{base}/models"))["data"][0]["id"]
    print(f"Model: {model}   endpoint: {base}   thinking: {args.thinking}\n")

    # Rozgrzewka (kompilacja grafów, CUDA graphs) — nie liczona.
    run_one(base, model, "Cześć", 8, False)

    rows = []
    print(f"{'prompt':>8} {'tryb':>5} {'TTFT [s]':>9} {'decode tok/s':>13} {'całość [s]':>11}")
    for n in args.lengths:
        prompt = build_prompt(n, uuid.uuid4().hex[:12])
        for mode in ("cold", "warm"):
            r = run_one(base, model, prompt, args.max_tokens, args.thinking, args.reasoning_effort_none)
            r.update({"target_tokens": n, "mode": mode})
            rows.append(r)
            print(f"{r['prompt_tokens'] or n:>8} {mode:>5} {r['ttft_s']:>9.2f} {str(r['decode_tok_s']):>13} {r['total_s']:>11.2f}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    # mlx_lm.server podaje jako id pełną ścieżkę do katalogu modelu — w wynikach tylko jego nazwa
    label = Path(model).name.lower() if model.startswith("/") else model
    result = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "platform": args.platform,
        "client_host": socket.gethostname(),
        "client_os": platform.platform(),
        "endpoint": base,
        "model": label,
        **({"model_path": model} if label != model else {}),
        "thinking": args.thinking,
        "max_tokens": args.max_tokens,
        "results": rows,
    }
    path = out_dir / f"{stamp}-{args.platform}-{label.replace('/', '_').replace(':', '-')}.json"  # „:” z tagów Ollamy
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nZapisano {path}")


if __name__ == "__main__":
    main()
