# spark-setup

Konfiguracja DGX Spark (`spark-28e3`) jako kod: przygotowanie hosta, manifest modeli,
serwowanie przez vLLM w kontenerach i pomiary. Cel: po resecie fabrycznym albo zmianie
sprzętu odtworzyć środowisko kilkoma poleceniami.

Repo nie zawiera sekretów (token HF w `.env`), wag modeli (odtwarzalne z `models.yaml`)
ani danych projektowych SOFA.

## Szybki start (od zera, po resecie)

Na Macu:

```bash
cat ssh/config.example >> ~/.ssh/config   # jednorazowo; dostosuj User/HostName
ssh-copy-id spark                         # jeśli klucza nie ma w ssh/authorized_keys
ssh spark
```

Na Sparku:

```bash
git clone git@github.com:<konto>/spark-setup.git && cd spark-setup
sudo ./bootstrap.sh michal        # pakiety, konto, grupy sudo/docker/llm, /data/hf, test GPU
# wyloguj się i zaloguj ponownie (nowe grupy)
cp .env.example .env && chmod 600 .env && nano .env   # HF_TOKEN
make models SET=c                 # ~40 GB do /data/hf
make up SET=c                     # vLLM: model na :8000, embeddingi na :8001
make logs                         # czekaj na "Application startup complete"
make test
make bench
```

Na Macu (przez tunel): `curl localhost:8000/v1/models`, OpenCode z `clients/opencode.json.example`.

## Struktura

| Ścieżka | Zawartość |
|---|---|
| `bootstrap.sh` | strefa czasowa, pakiety (w tym avahi dla `.local`), konto, grupy `sudo`/`docker`/`llm`, `/data/hf` i `/data/volumes` z setgid, klucze z `ssh/authorized_keys`, opcjonalnie utwardzenie SSH |
| `models.yaml` | manifest modeli: repo HF, rewizja, rozmiar, licencja, zestawy, warianty na inne platformy |
| `profiles/set-*.env` | zestawy: które modele, ile pamięci, długość kontekstu, parsery vLLM |
| `compose.yaml` | usługi `vllm-8000`, `embed-8001`, `vllm-8002`, `vllm-8003`, `vllm-8004`, `open-webui` (:8080); kontenery `spark-<port>-<model>`; porty tylko na `127.0.0.1` |
| `scripts/download_models.py` | pobieranie z manifestu (uruchamiane w kontenerze przez `make models`) |
| `scripts/render_env.py` | składa `.run.env` z `.env` + profilu + `models.yaml` |
| `bench/run_bench.py` | TTFT (zimny i z prefix cache) i tok/s; wyniki JSON w `bench/results/` |
| `ssh/` | wpis do `~/.ssh/config` z tunelami, klucze publiczne |
| `clients/` | konfiguracja OpenCode dla endpointu Sparka |

## Zestawy

| SET | Porty i modele | Pamięć (suma) | Kiedy | Stan |
|---|---|---|---|---|
| `b` | :8000 Qwen3.6-35B-A3B + :8002 Qwen3.8-27B + :8004 Gemma 4 26B-A4B (NVFP4) + :8001 bge-m3 | 0.82 | praca nad SOFA | Qwen zweryfikowane 2026-10-11 (cache 7,85 / 11,71 GiB); Gemma niezmierzona |
| `d` | :8003 Qwen3-Coder-Next + :8000 Qwen3.6-35B-A3B (NVFP4) + :8001 bge-m3 | 0.72 | praca z kodem (OpenCode na Macu przez tunel) | Coder-Next niezmierzony |
| `a` | :8000 gpt-oss-120b + :8001 bge-m3 | 0.69 | porównanie z zestawem B (przełączenie + ten sam test) | niezmierzony |
| `c` | :8000 Qwen3.6-35B-A3B (FP8) + :8001 bge-m3 | 0.61 | lekki start | niezmierzony |

Modele Qwen unikają tematów politycznie drażliwych w Chinach; Gemma 4 (:8004) to model ogólny
spoza tej rodziny.

Trzy duże modele (~20 GiB+ wag każdy, w tym Coder-Next ~43 GiB) naraz się nie mieszczą: każda instancja potrzebuje wagi + ok. 5–8 GiB
(grafy CUDA, bufory profilowania) + cache kontekstu. Zmierzone 2026-10-11: Qwen3.6 NVFP4 wagi
19,6 GiB, Qwen3.8 NVFP4 wagi 19,1 GiB (przy przydziale 0.20 zabrakło 3 GiB na cache).

Usługi startują po kolei (`vllm-8000` → `embed-8001` → `vllm-8002` → `vllm-8004`; `vllm-8003` po `embed-8001`), żeby nie
walczyły o pamięć. Pełny start zestawu trwa ok. 5–10 minut.

Zmiana zestawu (np. SOFA → kod): `make down && make up SET=d`. Nowy zestaw najpierw `make models SET=x`.

Pamięć: `*_GPU_MEM` to ułamek całej pamięci zunifikowanej (~119 GiB), który każda instancja
vLLM rezerwuje z góry. Suma w zestawie powinna zostać poniżej ~0.85–0.9. Przy błędzie OOM
na starcie: `make drop-caches`, potem mniejsze `*_GPU_MEM` albo `*_MAX_LEN`.

`--max-num-seqs` (w profilach 16, dla gpt-oss 32) ogranicza liczbę równoczesnych zapytań.
Domyślne 256 nie mieści się przy modelach z warstwami Mamba/DeltaNet (Qwen3.6/3.8/Coder-Next):
vLLM kończy start błędem `max_num_seqs (256) exceeds available Mamba cache blocks`.

## Polecenia

`make help` wypisuje wszystkie. Najważniejsze:

| Polecenie | Działanie |
|---|---|
| `make models SET=x` | pobranie modeli zestawu |
| `make pin SET=x` | aktualne SHA rewizji do wklejenia w `models.yaml` |
| `make up SET=x` / `make up-ui SET=x` | start usług; `up-ui` dodaje Open WebUI na :8080 (widzi modele z :8000, :8002, :8003) |
| `make status` | port → model → stan |
| `make log P=8000` | logi jednego modelu (8001 embeddingi, 8002, 8003) |
| `make errors` | same błędy i zużycie pamięci z logów wszystkich modeli |
| `make down`, `make logs` | zatrzymanie, logi wszystkich usług |
| `make test` | lista modeli i krótka odpowiedź |
| `make bench` | pomiar, wynik do `bench/results/` (commituj) |
| `make harden-ssh` | tylko klucze, bez roota, tylko twój użytkownik (gdy klucz na pewno działa) |

## Zasady

- Nic nie instalujemy przez pip na hoście; wszystko w kontenerach (vLLM z NGC pod ARM64/CUDA 13).
- Wersje obrazów (`.env`) i rewizje modeli (`models.yaml`) przypięte; po pierwszym udanym teście `make pin`.
- vLLM działa z `HF_HUB_OFFLINE=1`: używa tylko tego, co pobrał `make models`.
- Kopia zapasowa potrzebna tylko dla `/data/volumes` (np. Open WebUI) i `.env`; reszta jest odtwarzalna.

## Inne platformy

`models.yaml` → `variants` zawiera odpowiedniki na Maca (GGUF/MLX dla llama.cpp / LM Studio).
Klienci (OpenCode, skrypty, `bench/`) używają tego samego API zgodnego z OpenAI, więc zmienia się
tylko adres endpointu.
