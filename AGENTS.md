# spark-setup — instrukcje dla agentów (Claude Code, Cursor, OpenCode)

Odtwarzalna konfiguracja NVIDIA DGX Spark do lokalnej inferencji LLM (vLLM w kontenerach) na potrzeby PoC SOFA: analiza jakości wymagań i RAG nad modelami Enterprise Architect.

## Najpierw przeczytaj

| Plik | Co zawiera |
|---|---|
| `docs/backlog.md` | stan prac, najbliższe kroki, backlog B1… — **zacznij tutaj** |
| `docs/findings.md` | znaleziska, pomiary, zalecenia, procedura odzyskiwania, troubleshooting |
| `docs/decisions.md` | decyzje D-01… z uzasadnieniem i odrzuconymi alternatywami |
| `docs/context/` | materiały SOFA: `sofa-obserwacje.md` (koncepcja), `llm-pamiec-wzor.md` (pamięć, prefill/decode), `rag-ea-symulator.html` |

## Środowisko

| Element | Wartość |
|---|---|
| Spark | `spark-28e3.local` (mDNS), użytkownik `michal`, Ubuntu 24.04 (DGX OS), ARM64, GB10, CUDA 13 |
| Pamięć | 128 GB zunifikowanej; vLLM widzi 121,69 GiB (= `--gpu-memory-utilization 1.0`) |
| Laptop | MacBook Pro M4 Pro 48 GB (zsh); tu działa edytor i OpenCode |
| Dostęp | wyłącznie SSH; usługi na Sparku tylko na `127.0.0.1`, z Maca przez tunel `ssh -N spark` (porty 8000–8004, 8080) |
| Modele | `/data/hf` na Sparku (grupa `llm`, setgid); obraz `nvcr.io/nvidia/vllm:26.09-py3` (vLLM 0.29) |
| Repo | https://github.com/missiollo/spark-setup (prywatne); klon na Macu: `/Users/michalmariak/Documents/Projects/spark-setup`, na Sparku: `~/spark-setup` (`/home/michal/spark-setup`) |

Porty: 8000 model główny, 8001 embeddingi (bge-m3), 8002 Qwen3.8 (zestaw B), 8003 Qwen3-Coder-Next (zestaw D), 8004 Gemma 4 (zestaw B), 8080 Open WebUI.

## Struktura repo

- `models.yaml` — manifest modeli (repo HF, rewizja, zestawy). Rewizja tylko tutaj.
- `profiles/set-{a,b,c,d}.env` — zestawy: przydziały pamięci, kontekst, argumenty vLLM, `COMPOSE_PROFILES`.
- `scripts/render_env.py` — składa `.run.env` z `.env` + profilu + manifestu (role `LLM`, `LLM2`, `LLM3`, `LLM4`, `EMBED`).
- `compose.yaml` — usługi `vllm-8000`, `embed-8001`, `vllm-8002`, `vllm-8003`, `vllm-8004`, `open-webui`; start po kolei (healthcheck + `depends_on`).
- `Makefile` — `make help`; najważniejsze: `models`, `up`, `up-ui`, `down`, `status`, `log P=8000`, `errors`, `test`, `bench`, `drop-caches`.
- `bench/run_bench.py` — TTFT cold/warm i decode tok/s; wyniki JSON w `bench/results/`.
- `bootstrap.sh` — przygotowanie hosta po resecie.

## Uruchamianie poleceń na Sparku z Maca

`make`, `docker` i `nvidia-smi` działają tylko na Sparku. Edytor i agent pracują w klonie na Macu; Spark ma osobny klon, zsynchronizowany przez GitHub. Z Maca:

```bash
ssh -o ClearAllForwardings=yes spark 'cd ~/spark-setup && make status'
ssh -o ClearAllForwardings=yes spark 'cd ~/spark-setup && make errors'
```

`ClearAllForwardings=yes` jest konieczne: alias `spark` ma `LocalForward` z `ExitOnForwardFailure yes`, więc przy otwartym tunelu zwykłe `ssh spark '…'` kończy się błędem zajętego portu.

API modeli z Maca (przy otwartym tunelu): `curl -s localhost:8000/v1/models`.

Zmiany w repo: commit na Macu → `git push` → na Sparku `git pull` (obie maszyny mają `pull.rebase true`).

## Zasady

- Nie wprowadzaj pozycji z backlogu bez prośby użytkownika; nowe pomysły dopisuj do `docs/backlog.md`.
- Każde nowe znalezisko (objaw, przyczyna z logu, liczby, wniosek) zapisuj w `docs/findings.md` (nowa podsekcja 3.x z datą); decyzję w `docs/decisions.md`; zadania w `docs/backlog.md`. Komenda `/finding` w Claude Code robi to w jednym kroku.
- Liczby w dokumentacji tylko z pomiarów lub logów (`make errors`, `make bench`); szacunki oznaczaj jako szacunki.
- Przed zmianą przydziałów pamięci sprawdź zasadę z `findings.md` 3.3: przydział ≥ wagi + 1–8 GiB + cache; suma w zestawie ≤ ~0.85.
- Zawsze jawne `--max-num-seqs` (16; gpt-oss 32) — domyślne 256 blokuje modele hybrydowe (`findings.md` 3.2).
- Nic przez pip na hoście Sparka; wszystko w kontenerach. Porty tylko na `127.0.0.1`.
- Sekrety (`.env`, `HF_TOKEN`) nigdy w repo ani w logach.
- Nie uruchamiaj na Sparku bez potwierdzenia: `make down`, `make up*`, `docker rm`, `make models`, `bootstrap.sh`, `harden-ssh` — przerywają pracę modeli albo trwają długo (start zestawu 10–15 min, pobieranie ~30–60 min).
- Długie operacje na Sparku w `tmux` (przerwane `make up` zostawia kontenery w stanie `Created`).
- Polecenia dla użytkownika do wklejenia w zsh: bez komentarzy `#`, jedno polecenie na linię.

## Styl

- Dokumentacja i komentarze po polsku; nazwy plików, zmiennych, commitów po angielsku.
- Dokumenty: zwięzłe, tabele zamiast długiej prozy, daty w formacie RRRR-MM-DD, odwołania do sekcji (`findings.md` 3.6).
- Commity: krótki tytuł po angielsku w trybie rozkazującym (np. „Add Gemma 4 26B-A4B (NVFP4) on :8004 to set B”).
