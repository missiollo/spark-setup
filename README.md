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
| `compose.yaml` | usługi `llm` (:8000), `embed` (:8001), `llm2` (:8002), `llm3` (:8003), `open-webui` (:8080); porty tylko na `127.0.0.1` |
| `scripts/download_models.py` | pobieranie z manifestu (uruchamiane w kontenerze przez `make models`) |
| `scripts/render_env.py` | składa `.run.env` z `.env` + profilu + `models.yaml` |
| `bench/run_bench.py` | TTFT (zimny i z prefix cache) i tok/s; wyniki JSON w `bench/results/` |
| `ssh/` | wpis do `~/.ssh/config` z tunelami, klucze publiczne |
| `clients/` | konfiguracja OpenCode dla endpointu Sparka |

## Zestawy

| SET | Modele | Do pobrania | Stan |
|---|---|---|---|
| `c` | Qwen3.6-35B-A3B (FP8) + bge-m3 | ~40 GB | start; do sprawdzenia całego łańcucha |
| `b` | Qwen3.6-35B-A3B :8000 + Qwen3.8-27B :8002 + Qwen3-Coder-Next :8003 (wszystkie NVFP4) + bge-m3 | ~90 GB | uniwersalny: czat, jakość/SQL, kod naraz; nieprzetestowany |
| `a` | gpt-oss-120b + Qwen3.8-27B (FP8) + bge-m3 | ~96 GB | porównanie modeli dla SOFA; nieprzetestowany |
| `d` | Qwen3-Coder-Next (FP8) + bge-m3 | ~82 GB | asystent kodu; nieprzetestowany |

W zestawach z kilkoma modelami usługi startują po kolei (`llm` → `llm2` → `llm3`), żeby nie
walczyły o pamięć. Pełny start zestawu B może trwać kilkanaście minut.

Zmiana zestawu: `make down && make models SET=a && make up SET=a`.

Pamięć: `*_GPU_MEM` to ułamek całej pamięci zunifikowanej (~119 GiB), który każda instancja
vLLM rezerwuje z góry. Suma w zestawie powinna zostać poniżej ~0.85–0.9. Przy błędzie OOM
na starcie: `make drop-caches`, potem mniejsze `*_GPU_MEM` albo `*_MAX_LEN`.

## Polecenia

`make help` wypisuje wszystkie. Najważniejsze:

| Polecenie | Działanie |
|---|---|
| `make models SET=x` | pobranie modeli zestawu |
| `make pin SET=x` | aktualne SHA rewizji do wklejenia w `models.yaml` |
| `make up SET=x` / `make up-ui SET=x` | start usług; `up-ui` dodaje Open WebUI na :8080 (widzi modele z :8000, :8002, :8003) |
| `make down`, `make logs`, `make ps` | zarządzanie |
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
