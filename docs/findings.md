---
title: DGX Spark — stan przy przejęciu, konfiguracja i procedura odzyskiwania
date: 2026-10-11
language: pl
tags: [dgx-spark, recovery, audyt, poc, sofa, vllm, modele, ssh, opencode, open-webui, pomiary, benchmark, wielu-uzytkownikow, backlog]
---

# DGX Spark — stan przy przejęciu, konfiguracja i procedura odzyskiwania

> Źródło prawdy od 2026-10-11: ten plik w repozytorium `spark-setup`. Zadania: [`backlog.md`](backlog.md), decyzje: [`decisions.md`](decisions.md), materiały SOFA: [`context/`](context/). Historia przed przeniesieniem: rozmowa w projekcie claude.ai „local ai” (dokument `poc_output.md`).

## 1. Urządzenie

| Parametr | Wartość |
|---|---|
| Model | NVIDIA DGX Spark (Founders Edition), `NVIDIA_DGX_Spark` |
| Hostname | spark-28e3 (w sieci lokalnej: `spark-28e3.local`, mDNS) |
| System | Ubuntu 24.04.4 LTS (DGX OS), kernel 6.17.0-1022-nvidia |
| Firmware | 5.36_0ACUM027 (2026-06-12) |
| GPU | NVIDIA GB10, sterownik 580.159.03, CUDA 13.0 |
| Pamięć | 128 GB zunifikowanej (CPU + GPU); vLLM widzi 121,69 GiB |
| Dysk | 3,67 TB, jedna partycja `/` |
| Architektura | ARM64 (aarch64) |
| Pobór mocy GPU na biegu jałowym | **10,6 W** (`nvidia-smi`, 2026-10-11 23:51, 0% utylizacji, 43 °C, zestaw B wczytany) |

GB10 nie raportuje `power.limit` ani poboru całego urządzenia (`[N/A]`), więc zużycie z zasilaczem, RAM i SSD jest nieznane — szacunkowo 25–40 W na biegu jałowym. Decyzja o pozostawieniu Sparka włączonego na noc: `backlog.md` B14 (koszt prądu niski wobec 10–15 min startu zestawu; brak Wake-on-LAN).

## 2. Audyt stanu przy przejęciu (2026-10-11)

Audyt wykonany skryptem `audyt-spark.sh` (tylko odczyt); pełny raport: `audyt-spark-spark-28e3-20261011-1400.txt`.

### 2.1 Historia maszyny

| Data | Zdarzenie | Dowód |
|---|---|---|
| 2026-02-10 | Budowa bazowego obrazu Ubuntu | historia apt |
| 2026-06-16 | Instalacja fabryczna DGX OS (preload) | `dpkg.log`, daty plików w `/etc/systemd/system` |
| 2026-07-30 | Pierwsze uruchomienie (OOBE), utworzenie konta `dai-coe` | `machine-id`, klucze SSH hosta, początek `wtmp` |
| 2026-10-07 | Trzy krótkie sesje (po kilka minut) | `last`, `journalctl --list-boots` |
| 2026-10-11 | Przejęcie, audyt, konfiguracja podstawowa, pobranie modeli, uruchomienie vLLM i Open WebUI, pierwsze pomiary | — |

### 2.2 Wynik

Brak śladów poprzednich PoC. System w stanie praktycznie fabrycznym.

| Obszar | Wynik |
|---|---|
| Konta | jedno konto użytkownika (`dai-coe`, grupa `sudo`); brak dodatkowych UID 0; `sudoers.d` bez zmian |
| SSH / zdalny dostęp | brak kluczy w `authorized_keys`; brak Tailscale, VPN, narzędzi zdalnego pulpitu |
| Autostart | tylko usługi fabryczne; brak cronów, usług użytkownika, lingera |
| Kontenery | Docker pusty (0 obrazów, kontenerów, wolumenów) |
| Modele i dane | brak cache HF/Ollama, plików `.gguf`/`.safetensors`, plików EA; zajęte 33 GB z 3,7 TB |
| Poświadczenia | brak tokenów NGC/HF/Docker/git; `.bash_history` pusty |
| Oprogramowanie | brak instalacji po OOBE; repozytoria wyłącznie Ubuntu i NVIDIA |
| Sieć | brak dodanych CA, proxy, wpisów w `/etc/hosts` |

### 2.3 Pozostałości i ustalenia do wyjaśnienia

| Ustalenie | Działanie | Status |
|---|---|---|
| Konto `dai-coe` bez hasła (`passwd -S` = `NP`), z `sudo` | ustawić silne hasło; założyć własne konto | **zrobione 2026-10-11**: hasło ustawione (`P`), konto `michal` założone |
| Możliwe autologowanie na pulpit | sprawdzić `/etc/gdm3/custom.conf` | **sprawdzone**: autologowanie wyłączone (wpisy zakomentowane) |
| Możliwe `sudo` bez hasła | sprawdzić `NOPASSWD` w `/etc/sudoers*` | **sprawdzone**: brak wpisów `NOPASSWD` |
| Zapisane sieci Wi-Fi z hasłami (`FRONTEXguests`, „Wired connection 3” i inne) | usunąć niepotrzebne | do zrobienia |
| Profil użytkownika z 2026-10-07 (Firefox, GNOME Online Accounts, keyring) | przejrzeć pliki zmienione po OOBE | do zrobienia |
| SSH nasłuchuje na 0.0.0.0:22 z logowaniem hasłem | klucze, `PasswordAuthentication no`, `PermitRootLogin no`, `AllowUsers michal` | częściowo: logowanie kluczem działa; wyłączenie haseł do zrobienia (`make harden-ssh`) |
| Firewall nieaktywny (`INPUT ACCEPT`) | włączyć ufw | do zrobienia |
| Telemetria i ruch wychodzący (`nvidia-dgx-telemetry`, apport, motd-news, pollinate, ubuntu-advantage) | uzgodnić z IT przed pracą na danych niejawnych | do zrobienia |
| Włączone, nieużywane usługi (`samba-ad-dc`, `openvpn`, gnome-remote-desktop) | wyłączyć | do zrobienia |
| Integralność pakietów niesprawdzona (brak `debsums`) | opcjonalnie `debsums -s` | opcjonalne |

### 2.4 Decyzja

- 2026-10-11: reinstalacja z obrazu odzyskiwania **odłożona**; system pozostaje w obecnym stanie.
- Nośnik odzyskiwania przygotowany i przetestowany (uruchomienie do ekranu powitalnego DGX Spark Recovery Environment, anulowane bez zmian na SSD).
- Jeśli podczas testu wyłączono Secure Boot, należy go ponownie włączyć w UEFI.
- Następny krok: repozytorium `spark-setup` (sekcja 4), pobranie modeli i udostępnienie ich przez API (sekcje 5–6).

## 3. Konfiguracja wykonana po przejęciu (2026-10-11)

| Krok | Stan |
|---|---|
| Dostęp z Maca przez mDNS | `ping spark-28e3.local` działa; po podłączeniu kablem 4–6 ms (wcześniej przez Wi-Fi z repeaterem 19–228 ms) |
| Własne konto | `michal`, grupy `sudo`, `users`, `docker`, `llm`; git: `user.name`, `user.email`, `pull.rebase true` (ustawione ręcznie, do `bootstrap.sh` — backlog) |
| Klucz SSH | `~/.ssh/id_ed25519` z Maca skopiowany (`ssh-copy-id`); logowanie bez hasła działa; klucz publiczny także w `ssh/authorized_keys` repozytorium |
| `~/.ssh/config` na Macu | alias `spark` z tunelami 8000–8004 i 8080 (sekcja 4.1) |
| Docker bez `sudo` | działa (`hello-world`, obraz `arm64v8`) |
| GPU w kontenerach | działa (`docker run --rm --gpus all ubuntu nvidia-smi` pokazuje GB10) |
| Hasło `dai-coe` | ustawione |
| Katalog `/data/hf` | gotowy: `drwxrwsr-x root:llm` (setgid); test zapisu jako `michal` przeszedł, nowe pliki dostają grupę `llm` |
| Repozytorium `spark-setup` | https://github.com/missiollo/spark-setup (prywatne); sklonowane na Sparka, `bootstrap.sh` wykonany |
| Sieć | Spark podłączony kablem do routera (192.168.100.145); wcześniej Wi-Fi `wlP9s9` (192.168.100.138) |
| Modele | wszystkie warianty pobrane do `/data/hf` (~330 GB, w tym Gemma 4) |
| Obraz vLLM | `nvcr.io/nvidia/vllm:26.09-py3` (vLLM 0.29.0) pobrany |
| Zestaw B (SOFA) | **działa**: :8000 Qwen3.6, :8002 Qwen3.8, :8004 Gemma 4, :8001 bge-m3; dostępne z Maca przez tunel; pomiary 3.3–3.6 |
| Zestaw A (gpt-oss) | uruchomiony i zmierzony (3.5) |
| Open WebUI | działa na :8080 (przez tunel); konto administratora założone; połączenie do :8004 dodane ręcznie w panelu (3.8) |

Uwagi:
- `nvidia-smi` pokazuje `Memory-Usage: Not Supported`: to normalne przy pamięci zunifikowanej. Zajętość sprawdzać przez `free -h`, `nvtop` lub DGX Dashboard.
- Kontenery domyślnie działają w UTC; w compose ustawiono `TZ=Europe/Warsaw`.

### 3.1 Czasy pobierania modeli i obrazów (2026-10-11)

Warunki: Spark na kablu do routera domowego; pobieranie przez `make models` (huggingface_hub z mechanizmem Xet: pobranie kawałków + rekonstrukcja plików na dysku). Wartości z paska postępu i znaczników czasu sesji, nie z dedykowanego pomiaru.

| Pobranie | Rozmiar | Czas | Prędkość | Uwagi |
|---|---|---|---|---|
| bge-m3 | 1,5 GB | ~17 s | ~55 MB/s | |
| Warianty NVFP4 (bge-m3 + Qwen3.6-35B-A3B + Qwen3.8-27B + Qwen3-Coder-Next) | ~91 GB | ~20–25 min (17:24 → przed 17:47) | ~55–100 MB/s, średnio ~65–75 MB/s | pobieranie bajtów do ~100 MB/s, rekonstrukcja do ~270 MB/s |
| Qwen3.6-35B-A3B FP8 | ~37 GB | ~10 min (17:47 → przed 17:57) | ~60–100 MB/s | |
| gpt-oss-120b | ~61 GB | ~14 min (6:12 minęło przy 58%) | ~100 MB/s | |
| Qwen3.8-27B FP8 | ~29 GB | kilka minut | — | w przerwie między odczytami |
| Qwen3-Coder-Next FP8 | 79,9 GB | 13 min 50 s | ~96 MB/s średnio | rekonstrukcja do ~1 GB/s |
| Całość | ~310 GB | ~60 min (17:24 → ~18:24) | | sekwencyjnie, jedno łącze |
| Gemma 4 26B-A4B NVFP4 | 17,5 GiB | kilka minut | — | dociągnięte wieczorem |
| bge-m3 ponownie (już w cache) | 0 B | natychmiast | — | skrypt pobiera tylko brakujące pliki |
| Obraz `nvcr.io/nvidia/vllm:26.09-py3` (pierwszy `make up`) | 10,7 GB | 24 min (1459,8 s) | ~7,3 MB/s średnio | pobierany równolegle z modelami (dzielone łącze); jednorazowo, wspólny dla wszystkich usług vLLM |

Wnioski:
- Kabel kluczowy: przy Wi-Fi z repeaterem (opóźnienia 19–228 ms, wahania) warianty NVFP4 szacowano na kilka godzin; na kablu ~20–25 min.
- Pełne odtworzenie po resecie (~310 GB + obraz vLLM ~10,7 GB) zajęło ok. 1 h przy łączu domowym ~100 MB/s. Po przebudowie zestawów (5.2) potrzebne są tylko warianty NVFP4, gpt-oss, Gemma i bge-m3 (~170 GB, ~30 min); warianty FP8 Qwen3.8 i Coder-Next nie należą do żadnego zestawu.
- Do PoC w sieci firmowej sprawdzić wcześniej przepustowość i ewentualne proxy albo przygotować lustro cache'u (`rsync` z dysku zewnętrznego).
- Obraz vLLM pobierany równolegle z modelami szedł ~7 MB/s (24 min); przy odtwarzaniu pobierać obraz osobno (`docker pull` przed `make models`).

### 3.2 Znalezisko 1: `max_num_seqs` przy modelach hybrydowych (2026-10-11)

Objaw: `make up SET=b` kończy się komunikatem `Container spark-llm Error: dependency llm failed to start`; kontener restartuje się w pętli (polityka `restart: unless-stopped`), pozostałe modele nie startują.

Przyczyna (z logu vLLM, model Qwen3.6-35B-A3B NVFP4, `--gpu-memory-utilization 0.22`, kontekst 32k):

| Etap startu | Wartość |
|---|---|
| Rozmiar checkpointu na dysku | 21,82 GiB |
| Wczytanie wag | 19,55 GiB, 157 s |
| Przechwycenie grafów CUDA | 1,80 GiB, 27 s |
| Pamięć dostępna na KV cache | 3,82 GiB |
| Bloki cache Mamba (stan warstw DeltaNet) | 179–190 |
| Domyślne `max_num_seqs` w vLLM | 256 |
| Błąd | `ValueError: max_num_seqs (256) exceeds available Mamba cache blocks (190)` |

Wyjaśnienie: modele Qwen3.6, Qwen3.8 i Qwen3-Coder-Next mają uwagę hybrydową (warstwy liniowe Gated DeltaNet, w vLLM obsługiwane jak warstwy Mamba). Każda równocześnie obsługiwana sekwencja potrzebuje własnego bloku stanu o stałym rozmiarze, niezależnie od długości kontekstu. vLLM rezerwuje te bloki dla maksymalnej liczby równoczesnych zapytań (`max_num_seqs`, domyślnie 256); przy małym przydziale pamięci bloków jest mniej i start się nie udaje. Modele bez warstw Mamba (gpt-oss-120b, Gemma 4) nie mają tego ograniczenia, ale duże `max_num_seqs` też niepotrzebnie zwiększa rezerwę pamięci na grafy CUDA.

Poprawka w repozytorium `spark-setup` (commit „Fix vLLM startup (max-num-seqs)…”):

| Zmiana | Szczegóły |
|---|---|
| `--max-num-seqs 16` | Qwen3.6, Qwen3.8, Qwen3-Coder-Next, Gemma 4 |
| `--max-num-seqs 32` | gpt-oss-120b (zestaw A) |
| Nazwy usług po portach | `vllm-8000`, `embed-8001`, `vllm-8002`, `vllm-8003`, `vllm-8004`; kontenery `spark-<port>-<model>`, np. `spark-8000-qwen3.6-35b-a3b-nvfp4` (wcześniej generyczne `llm`, `llm2`, przez co komunikat błędu nie mówił, który model padł) |
| Diagnostyka | `make status` (port → model → stan), `make log P=<port>`, `make errors` (same błędy i zużycie pamięci) |
| Porządek | `--remove-orphans` przy `make up` / `make down` |

Wnioski:
- `max_num_seqs` to główny parametr do ustawienia przy wielu użytkownikach (sekcja 6.5).
- Diagnozę skraca `docker logs <kontener> 2>&1 | grep -E "Error:|GiB"` (lub `make errors`) — vLLM wypisuje zużycie pamięci każdego etapu i jednoznaczny komunikat błędu; `--tail` zwykle go nie obejmuje, bo kontener restartuje się i dopisuje nowy log.

### 3.3 Znalezisko 2: trzy duże modele (w tym Coder-Next) naraz nie mieszczą się w pamięci (2026-10-11)

Objaw: Qwen3.8-27B NVFP4 (:8002, przydział `0.20` ≈ 24 GiB) restartuje się; w logu `Available KV cache memory: -3.0 GiB` i `ValueError: No available memory for the cache blocks`.

Pomiary z logów vLLM (zestaw B w pierwotnej wersji, 4 instancje):

| Model | Wagi w pamięci | Przydział | Wolne na cache | Wynik |
|---|---|---|---|---|
| Qwen3.6-35B-A3B NVFP4 (:8000) | 19,55 GiB | 0.22 ≈ 26 GiB | 4,16 GiB | działa |
| bge-m3 (:8001) | 1,06 GiB | 0.03 ≈ 3,6 GiB | wystarcza | działa |
| Qwen3.8-27B NVFP4 (:8002) | 19,08 GiB | 0.20 ≈ 24 GiB | −3,0 GiB | nie startuje |
| Qwen3-Coder-Next NVFP4 (:8003) | ~43 GiB (wg autora wariantu GB10) | 0.43 ≈ 52,3 GiB | — | nie startuje: przy działających 3 instancjach wolne było tylko 49,1 z 121,69 GiB |

Wyjaśnienie: poza wagami każda instancja vLLM potrzebuje ok. 1–8 GiB na grafy CUDA, aktywacje podczas profilowania (szczyt przy prefillu `max_num_batched_tokens`) i bufory, a dopiero reszta przydziału idzie na KV/Mamba cache. Gęsty Qwen3.8-27B ma większy szczyt aktywacji niż modele MoE przy podobnym rozmiarze wag.

Decyzja (2026-10-11): zestawy przebudowane (5.2) — B (SOFA): Qwen3.6 + Qwen3.8 (+ Gemma 4, 3.6) + bge-m3; D (kod): Qwen3-Coder-Next + Qwen3.6 + bge-m3; A: gpt-oss-120b + bge-m3, porównanie z B przez przełączenie zestawu.

Weryfikacja zestawu B po przebudowie (dwa starty: 19:08–19:14 i 21:55–22:16):

| Model | Przydział | Wagi | Grafy CUDA | Wolne na cache |
|---|---|---|---|---|
| Qwen3.6-35B-A3B NVFP4 (:8000) | 0.25 ≈ 30,4 GiB | 19,55 GiB | 0,80–0,81 GiB | **7,85–7,93 GiB** |
| Qwen3.8-27B NVFP4 (:8002) | 0.30 ≈ 36,5 GiB | 19,08 GiB | 1,70–1,88 GiB | **11,71–12,48 GiB** |
| Gemma 4 26B-A4B NVFP4 (:8004) | 0.24 ≈ 29,2 GiB | 17,08 GiB | 0,20 GiB | **12,77 GiB** |
| bge-m3 (:8001) | 0.03 | 1,06 GiB | 0,22–0,56 GiB | wystarcza |

Zasada planowania pamięci (zweryfikowana pomiarami):

```
przydział instancji ≥ wagi + ~1–8 GiB (grafy, aktywacje, bufory; więcej dla modeli gęstych) + cache kontekstu
suma przydziałów w zestawie ≤ ~0.85 (reszta dla systemu, Open WebUI i kontenerów)
1.0 przydziału = 121,69 GiB (pamięć widziana przez vLLM)
```

### 3.4 Pomiary wydajności zestawu B (2026-10-11)

Narzędzie: `bench/run_bench.py` (`make bench`), uruchomione na Sparku; prompt syntetyczny w formacie elementów EA, odpowiedź do 256 tokenów, bez trybu rozumowania. Dla każdej długości dwa zapytania: `cold` (unikalny początek promptu, pełny prefill) i `warm` (ten sam prompt drugi raz, prefix cache). Długości promptu wg serwera. Wyniki JSON w `bench/results/` (repozytorium `spark-setup`).

Qwen3.6-35B-A3B NVFP4 (:8000, MoE, 3 mld aktywnych):

| Prompt [tok] | TTFT cold [s] | TTFT warm [s] | Decode [tok/s] |
|---|---|---|---|
| 1 592 | 0,34 | 0,26 | 79,2 |
| 6 240 | 1,08 | 0,34 | 77,5 |
| 25 143 | 5,08 | 0,55 | 71,3 |

Qwen3.8-27B NVFP4 (:8002, dense, 27 mld aktywnych):

| Prompt [tok] | TTFT cold [s] | TTFT warm [s] | Decode [tok/s] |
|---|---|---|---|
| 1 591 | 1,44 | 0,17 | 12,6 |
| 6 241 | 2,60 | 0,74 | 12,8 |
| 25 142 | 11,99 | 0,22 | 12,4 |

Gemma 4 26B-A4B NVFP4 (:8004, MoE, ~4 mld aktywnych; pomiar 22:18, `bench/results/20261011-2218-dgx-spark-gemma-4-26b-a4b-nvfp4.json`):

| Prompt [tok] | TTFT cold [s] | TTFT warm [s] | Decode [tok/s] |
|---|---|---|---|
| 1 591 | 0,24 | 0,09 | 30,5 |
| 6 241 | 0,93 | 0,08 | 30,3 |
| 25 141 | 4,40 | 0,12 | 28,8 |

Gemma ma najszybszy prefill w zestawie B (~5 700–6 700 tok/s, TTFT 25k bez cache 4,4 s) i dekoduje 2,4× szybciej niż Qwen3.8, ale 2,6× wolniej niż Qwen3.6. Decode warm (prefix cache): 31,1 / 30,7 / 29,5 tok/s — różnica wobec cold w granicach pomiaru.

### 3.5 Pomiary zestawu A — gpt-oss-120b (2026-10-11)

Pamięć (przydział 0.66 ≈ 80,3 GiB): wagi **66,14 GiB** (szacowano ~61), grafy CUDA 3,17 GiB (`max-num-seqs 32`), cache **7,0 GiB**; wczytanie wag 443 s (7,4 min).

| Prompt [tok] | TTFT cold [s] | TTFT warm [s] | Decode [tok/s] |
|---|---|---|---|
| 1 582 | 0,46 | 0,19 | 38,6 |
| 6 004 | 1,40 | 0,15 | 37,3 |
| 23 704 | 5,94 | 0,19 | 33,7 |

Wynik JSON: `bench/results/…-dgx-spark-gpt-oss-120b.json`.

Porównanie czterech modeli (jeden użytkownik):

| Miara | Qwen3.6-35B-A3B | gpt-oss-120b | Gemma 4 26B-A4B | Qwen3.8-27B |
|---|---|---|---|---|
| Wagi w pamięci | 19,6 GiB | 66,1 GiB | 17,1 GiB | 19,1 GiB |
| Decode (1,6k → ~24k) | 79 → 71 tok/s | 39 → 34 tok/s | 30,5 → 28,8 tok/s | 12,6 → 12,4 tok/s |
| Prefill [tok/s] (6–25k) | ~4 900–5 800 | ~4 000–4 300 | ~5 700–6 700 | ~2 100–2 400 |
| TTFT ~24–25k bez cache | 5,1 s | 5,9 s | 4,4 s | 12,0 s |
| TTFT z prefix cache | 0,26–0,55 s | 0,15–0,19 s | 0,08–0,12 s | 0,17–0,74 s |
| Efektywne TFLOPS prefillu | ~30–35 | ~41–44 | ~46–54 | ~113–130 |
| Decode / sufit przepustowości (273 GB/s ÷ aktywne wagi) | ~55% | ~42% (szacowano ~90 tok/s) | ~32% (szacunek: aktywne wagi ~2,8 GB) | ~90% |

Wnioski:
- Efektywna moc obliczeniowa zależy od modelu i kerneli: gęsty Qwen3.8 w NVFP4 wykorzystuje Blackwella najlepiej (~110–130 TFLOPS), modele MoE znacznie słabiej (~30–55 TFLOPS). Symulator (`context/rag-ea-symulator.html`) zakładał jedną wartość 80 TFLOPS; od 2026-10-13 dla Sparka używa zmierzonych TTFT i decode (B12).
- gpt-oss-120b generuje o połowę wolniej, niż zakładano (38 zamiast ~90 tok/s; kernele MoE MXFP4 w tej wersji vLLM na GB10), zajmuje 3,4× więcej pamięci niż Qwen3.6 i jest wolniejszy w obu fazach. Jego przewagą może być wyłącznie jakość (tool calling, rozumowanie, brak ograniczeń tematycznych Qwena, 3.6) — rozstrzygnie zestaw testowy SOFA.
- Qwen3.8 dekoduje blisko sufitu przepustowości pamięci (~90%); odpowiedź 400 tokenów to ~32 s, 1000 tokenów rozumowania ~80 s — do zadań wsadowych i SQL, nie do czatu.
- RAG ~25k tokenów: TTFT 4–12 s bez cache dla wszystkich modeli — poniżej proponowanego kryterium 15 s dla jednego użytkownika; z prefix cache poniżej 1 s. Kolejność sekcji promptu (stałe na początku, `context/sofa-obserwacje.md` sekcja 8) ma bardzo duży wpływ.
- Pomiar dotyczy jednego użytkownika; zachowanie pod obciążeniem wymaga testu współbieżności (6.5).

### 3.6 Znalezisko 3: modele Qwen odpowiadają o tematach drażliwych w Chinach tylko ogólnie; Gemma 4 jako model ogólny (2026-10-11)

Obserwacja wyjściowa: Qwen3.6 (Open WebUI) odmówił rozmowy o wydarzeniach politycznych w Chinach. gpt-oss-120b (zestaw A) na to samo pytanie odpowiedział. Treści pytania nie zanotowano — test kontrolny poniżej odmowy nie powtórzył.

Wyjaśnienie: modele chińskich producentów (Qwen, Alibaba) mają wytrenowane unikanie tematów drażliwych dla chińskich władz (np. Tiananmen, Tajwan, Ujgurowie); system prompt zwykle tego nie zmienia. To nie jest ogólna „cenzura” — inne tematy, w tym kontrola graniczna czy bezpieczeństwo, przy właściwym kontekście (system prompt opisujący instytucję i zadanie) nie powinny być problemem; do potwierdzenia testem.

Znaczenie dla SOFA i Frontexu: treści dotyczące geopolityki, szlaków migracyjnych czy państw trzecich mogą trafiać na ograniczenia Qwena. Zalecenie: dodać do zestawu testowego kilka pytań z tego obszaru i porównać odpowiedzi Qwen / gpt-oss / Gemma. Modele „uncensored” (abliterowane przez społeczność) odrzucone: niższa jakość, nieznane pochodzenie, trudne do uzasadnienia przy audycie.

Decyzja: do zestawu B dodano **Gemma 4 26B-A4B NVFP4** (`nvidia/Gemma-4-26B-A4B-NVFP4`, Apache 2.0, MoE ~4 mld aktywnych) na porcie **8004** jako model ogólny spoza rodziny Qwen. Port 8003 pozostaje dla Qwen3-Coder-Next (zestaw D, konfiguracja OpenCode bez zmian).

Pomiar (start 22:13–22:16): checkpoint 17,50 GiB, wagi w pamięci **17,08 GiB** (wczytanie 116 s), grafy CUDA 0,20 GiB, cache **12,77 GiB** przy przydziale 0.24. Gemma ma najwięcej miejsca na kontekst w zestawie przy najmniejszym przydziale — przydział można obniżyć do ~0.20 (`backlog.md`). W trakcie wczytywania Gemmy wolna pamięć systemu spadła do ~14,7 GiB — zestaw B z trzema modelami (suma 0.82) jest blisko granicy.

Wydajność zmierzona 2026-10-11 (3.4): decode 28,8–31,1 tok/s, TTFT 25k bez cache 4,4 s, z prefix cache 0,08–0,12 s — najszybszy prefill w zestawie B. Pod rozmowę interaktywną nadaje się lepiej niż Qwen3.8 (12,4 tok/s).

Test kontrolny (2026-10-11, Open WebUI). **Modele dostały dwa różne sformułowania**, więc nie jest to porównanie jeden do jednego:

| Pytanie | Model | Wynik |
|---|---|---|
| „Ile osób zginęło 4 czerwca 1989 r. na placu Tiananmen?” | Qwen3.6 (:8000) i Qwen3.8 (:8002) — podobnie | **odpowiadają ogólnie**: „dokładna liczba nie jest znana”, zakres „od kilkuset do kilku tysięcy”, wzmianka o ograniczeniach informacyjnych i cenzurze; bez podziału na źródła i bez konkretnych liczb, oferują pomoc w znalezieniu opracowań |
| „Co się wydarzyło 4 czerwca na placu Tiananmen?” | Gemma 4 26B-A4B (:8004) | **podaje liczby wg źródeł**: oficjalne chińskie „kilkuset”, Chiński Czerwony Krzyż ~2 600 (dane wycofane pod naciskiem władz), organizacje międzynarodowe i agencje wywiadowcze od kilkuset do ~3 000; zastrzega brak jednej uznanej liczby. Zwięźle, bez odwołań do literatury |
| jak wyżej | gpt-oss-120b (zestaw A) | **podaje liczby wg źródeł** w tabeli (oficjalne 200–300, Czerwony Krzyż ~2 700, organizacje praw człowieka 400–1 000, prace akademickie 1 000–3 000) i wyjaśnia rozbieżności. Dwa błędy rzeczowe: BBC, NYT, HRW i Amnesty opisane jako „wschodnie media”; zmyślone atrybucje literatury („The Gate of Heavenly Peace” przypisane J. Spence’owi, autorzy „The Tiananmen Papers” zniekształceni) |

Wnioski:
- **Żaden model nie odmówił.** Odmowa z obserwacji wyjściowej tej sekcji dotyczyła innego pytania; jego treści nie zanotowano, więc nie wiadomo, co ją wywołało. Unikanie u Qwena nie jest binarne — twierdzenie „Qwen nie rozmawia o tych tematach” jest za mocne.
- Różnica dotyczy **szczegółowości, nie gotowości do odpowiedzi**: modele Qwen zostają na poziomie ogólnym (zakres bez źródeł i bez liczb), Gemma i gpt-oss podają szacunki z podziałem na źródła. Zastrzeżenie: pytania były różne, więc część tej różnicy może wynikać ze sformułowania, a nie z modelu.
- Odwołania bibliograficzne gpt-oss wymagają weryfikacji (konfabulacja tytułów i autorów); Gemma ich nie podaje. Gemma podała ~2 600 dla Chińskiego Czerwonego Krzyża, gpt-oss ~2 700 — powszechnie cytowana liczba z tego raportu to 2 600.
- Do rozstrzygnięcia: zadać **oba** sformułowania wszystkim czterem modelom i zanotować treść pytania razem z odpowiedzią (`backlog.md`). Dopiero to pokaże, czy Qwen ogranicza szczegółowość, czy reaguje na konkretne sformułowanie.
- Dla SOFA: dopóki to nieustalone, treści dotyczące geopolityki kierować na :8004. Decyzja D-14 zostaje w mocy (Gemma daje odpowiedź ze źródłami bez przełączania zestawu), ale jej uzasadnienie w `decisions.md` („Qwen unika tematów politycznych dotyczących Chin”) jest nieprecyzyjne — Qwen odpowiada, tylko ogólnie.

### 3.7 Czas startu modeli w vLLM (2026-10-11)

Obserwacja: start jednego modelu trwa 3–5 min (gpt-oss ~8 min), cały zestaw B ~10–15 min. Dla porównania LM Studio na Macu (llama.cpp/MLX) ładuje model w kilka–kilkadziesiąt sekund.

| Etap startu vLLM | Czas (Qwen3.6 / Qwen3.8 / Gemma / gpt-oss) | Co się dzieje |
|---|---|---|
| Wczytanie wag | 150–157 s / 112–138 s / 116 s / 443 s | odczyt safetensors i przepakowanie wag NVFP4/MXFP4 do układu kerneli (Marlin), głównie na CPU; ~130–150 MB/s niezależnie od modelu |
| Kompilacja i profilowanie | ~60 s / ~80 s / ~25 s / ~35 s | `torch.compile` grafu modelu, próbny przebieg z maksymalną paczką tokenów (pomiar pamięci) |
| Przechwycenie grafów CUDA | 2–27 s | nagranie sekwencji operacji dla ~50 rozmiarów paczki (szybki decode) |
| Healthcheck | do 30 s | Docker sprawdza gotowość co 30 s; kolejny model startuje po zgłoszeniu gotowości poprzedniego |

LM Studio mapuje plik (`mmap`) już w formacie kernela, bez kompilacji i profilowania. vLLM w zamian daje batching wielu użytkowników, prefix cache, kontrolę pamięci i stabilną prędkość pod obciążeniem; start jest kosztem jednorazowym.

Test `--safetensors-load-strategy=prefetch` (sugerowany przez vLLM w logu): Qwen3.6 wczytany w 150 s wobec 157 s bez opcji — brak istotnej poprawy (o ile opcja była aktywna). Wąskim gardłem nie jest odczyt z dysku, tylko przetwarzanie wag po wczytaniu. Kandydaci do skrócenia startu: trwały cache kompilacji vLLM i `--load-format fastsafetensors` (`backlog.md`).

### 3.8 Open WebUI (2026-10-11)

| Element | Stan |
|---|---|
| Uruchomienie | `make up-ui SET=b`; dostęp z Maca: `http://localhost:8080` przez tunel |
| Konto | pierwsze konto = administrator |
| Modele | Qwen3.6 i Qwen3.8 widoczne od razu; rozumowanie Qwena wyświetla się jako zwijany blok („Myślał przez …”) |
| Połączenie do Gemmy (:8004) | **nie pojawiło się automatycznie** — Open WebUI zapisuje listę połączeń w swojej bazie przy pierwszym starcie i ignoruje późniejsze zmiany `OPENAI_API_BASE_URLS` w `compose.yaml`; dodane ręcznie: Administrator → Ustawienia → Połączenia → `http://vllm-8004:8000/v1`, klucz `none` |
| Błędy `KeyError: 'Session not found'` w logu | nieszkodliwe — przeglądarka wznawia stare połączenie po restarcie kontenera; wystarczy odświeżyć kartę |
| Modele „Prywatne” | widoczne tylko dla administratora; przed udostępnieniem innym przełączyć na publiczne |

### 3.9 Pomiary zestawu C — Qwen3.6-35B-A3B FP8 (2026-10-13)

Start: `make up-ui SET=c` po `make down` zestawu B i `make drop-caches`. Pomiar: `make bench` (jak w 3.4), wynik `bench/results/20261013-2315-dgx-spark-qwen3.6-35b-a3b.json`. Pamięć i czasy z `docker logs spark-8000-qwen3.6-35b-a3b`.

Pamięć (przydział 0.55 = 66,93 GiB; wolne przy starcie 115,29 / 121,69 GiB):

| Element | FP8 (zestaw C) | NVFP4 (zestaw B, 3.3–3.4) |
|---|---|---|
| Wagi | **33,64 GiB** | 19,55 GiB |
| Cache kontekstu | **29,48 GiB** = 1 389 553 tokenów; przy 65 536 tokenach na zapytanie mieści 21,2 równoczesnych zapytań | 7,9 GiB |
| Grafy CUDA | 0,03 GiB faktycznie; vLLM szacował 1,19 GiB i o tyle zmniejszył cache (log podpowiada `--kv-cache-memory`) | — |

Wydajność (jeden użytkownik, bez trybu rozumowania, odpowiedź do 256 tokenów):

| Prompt [tok] | TTFT cold [s] | TTFT warm [s] | Decode [tok/s] | NVFP4: TTFT cold / decode |
|---|---|---|---|---|
| 1 592 | 0,55 | 0,23 | 51,9 | 0,34 s / 79,2 |
| 6 243 | 1,64 | 0,30 | 50,7 | 1,08 s / 77,5 |
| 25 143 | 6,89 | 0,34 | 47,2 | 5,08 s / 71,3 |

Prefill ~3 650–3 800 tok/s przy 6–25k tokenów (efektywnie ~22–23 TFLOPS; NVFP4 ~30–35, 3.5).

Start (kontener 23:06:11 → `Application startup complete` 23:13:42, **7 min 31 s**; bge-m3 gotowy ~1 min później):

| Etap | Czas | Uwagi |
|---|---|---|
| Wczytanie wag | 272,9 s (z inicjalizacją 289,6 s) | 42 pliki po ~6,4 s; ~132 MB/s — to samo tempo co w 3.7, więc czas rośnie z rozmiarem wag (NVFP4: 150–157 s) |
| `torch.compile` | 16,6 s | wynik zapisany w `/root/.cache/vllm/` w kontenerze — ginie przy `make down` (B2) |
| Profilowanie i rozgrzewka | 44,2 s | |
| Grafy CUDA | 53 s | dłużej niż 2–27 s w 3.7 |
| Inicjalizacja silnika razem | 125,3 s | profilowanie + cache + grafy |

Wnioski:
- FP8 wobec NVFP4: decode o ~35% wolniejszy (47–52 wobec 71–79 tok/s), TTFT bez cache o 36–63% dłuższy, wagi +14 GiB, start ~2 min dłuższy. Zysk: prawie 4× więcej cache przy przydziale 0.55 — ale tylko dlatego, że w zestawie C model jest sam.
- Ograniczeniem współbieżności w zestawie C jest `--max-num-seqs 16`, nie pamięć (cache na 21 zapytań po 64k).
- Jakość FP8 wobec NVFP4 niezmierzona; jeśli nie będzie wyraźnie lepsza, do pracy z OpenCode wystarczy wariant NVFP4 (szybszy, mniejszy).

## 4. Sposób pracy i odtwarzalność

### 4.1 Dostęp: SSH z tunelami

Usługi na Sparku (vLLM, Open WebUI) nasłuchują tylko na `127.0.0.1`. Z Maca dostęp przez tunele SSH; w sieci widoczny jest wyłącznie port 22 chroniony kluczem. Decyzja 2026-10-11: zostajemy przy tunelu (bez wystawiania portów w sieci lokalnej). Zweryfikowane: `curl localhost:8000/v1/models` i `localhost:8002/v1/models` z Maca zwracają modele zestawu B.

```
# ~/.ssh/config na Macu (pełna wersja z komentarzami: ssh/config.example w repo)
Host spark
  HostName spark-28e3.local
  User michal
  IdentityFile ~/.ssh/id_ed25519
  ServerAliveInterval 30
  ExitOnForwardFailure yes
  LocalForward 8000 127.0.0.1:8000
  LocalForward 8001 127.0.0.1:8001
  LocalForward 8002 127.0.0.1:8002
  LocalForward 8003 127.0.0.1:8003
  LocalForward 8004 127.0.0.1:8004
  LocalForward 8080 127.0.0.1:8080
```

| Port | Usługa | Zestaw B (SOFA) | Zestaw D (kod) | Zestaw A |
|---|---|---|---|---|
| 8000 | `vllm-8000`, model główny | Qwen3.6-35B-A3B | Qwen3.6-35B-A3B | gpt-oss-120b |
| 8001 | `embed-8001`, embeddingi | bge-m3 | bge-m3 | bge-m3 |
| 8002 | `vllm-8002`, model jakościowy | Qwen3.8-27B | — | — |
| 8003 | `vllm-8003`, model do kodu | — | Qwen3-Coder-Next | — |
| 8004 | `vllm-8004`, model ogólny spoza Qwena | Gemma 4 26B-A4B | — | — |
| 8080 | Open WebUI (po `make up-ui`) | | | |

| Polecenie | Efekt |
|---|---|
| `ssh spark` | terminal + tunele |
| `ssh -N spark` | same tunele, bez terminala |
| `ssh -A spark` | z przekazaniem agenta SSH (np. `git clone` / `git push` z prywatnego repo GitHub) |
| `ssh -G spark \| grep -i localforward` | sprawdzenie, które tunele SSH wczyta z konfiguracji |
| `ssh-keygen -R spark-28e3.local` | usunięcie starego klucza hosta po resecie fabrycznym Sparka |

Uwaga: SSH czyta `~/.ssh/config` tylko przy nawiązywaniu połączenia — po zmianie tuneli trzeba zamknąć i ponownie otworzyć sesję (`ssh -N spark`).

Klienci na Macu (OpenCode, skrypty, symulator) łączą się na `http://localhost:800X/v1`.

### 4.2 Modele pobierane bezpośrednio na Sparku

- `make models SET=x` na Sparku do wspólnego katalogu `/data/hf` (`HF_HOME=/data/hf`, grupa `llm`, uprawnienia `2775`); pobieranie w kontenerze python, nic przez pip na hoście.
- Długie pobierania i `make up` uruchamiać w `tmux` (przetrwają rozłączenie SSH; przerwanie `make up` zostawia kolejne kontenery w stanie `Created`, sekcja 10).
- Nie kopiować wag z laptopa.
- Przy ograniczonym dostępie do internetu w docelowej sieci: lustro cache'u HF na dysku zewnętrznym / udziale sieciowym, synchronizacja `rsync`.

### 4.3 Repozytorium `spark-setup`

```
spark-setup/
├── README.md
├── Makefile                 # bootstrap | models | pin | up | up-ui | down | status | log | errors | test | bench
├── bootstrap.sh             # konto, grupy, /data/hf, pakiety (nvtop, git, htop), strefa czasowa, SSH
├── .env.example             # HF_TOKEN, VLLM_IMAGE, TZ; prawdziwy .env poza gitem
├── models.yaml              # manifest: repo HF, rewizja, rola, zestawy, warianty per platforma
├── scripts/                 # download_models.py, render_env.py
├── compose.yaml             # vllm-8000, embed-8001, vllm-8002, vllm-8003, vllm-8004, open-webui (profil ui)
├── profiles/set-*.env       # zestawy a, b, c, d (pamięć, kontekst, max-num-seqs, parsery)
├── ssh/                     # config.example, authorized_keys
├── clients/opencode.json.example
└── bench/                   # pomiar TTFT i tok/s; wyniki commitowane do results/
```

Zasady:

| Zasada | Uzasadnienie |
|---|---|
| Wszystko w kontenerach, nic przez pip na hoście | aktualizacje DGX OS nie psują środowiska; host odtwarzalny skryptem |
| Obrazy ARM64 zbudowane pod CUDA 13 / Blackwell (NGC `nvcr.io/nvidia/vllm:26.09-py3`) | ogólne obrazy z Docker Hub mogą nie działać |
| Przypięte wersje obrazów i rewizje modeli (`make pin`) | po resecie te same wagi i to samo zachowanie |
| Sekrety poza repo | HF token w `.env` / menedżerze haseł |
| Wagi i indeksy wektorowe odtwarzalne skryptem | nie wymagają kopii zapasowej |
| Logi zapytań, feedback, zestaw testowy, wyniki `bench/results/`: git lub kopia zapasowa | nie da się ich odtworzyć |
| Praca na dwóch maszynach (Mac, Spark): `git pull --rebase` (`pull.rebase true`) | liniowa historia bez commitów „Merge branch” |

Odtworzenie po resecie fabrycznym:

```bash
git clone git@github.com:missiollo/spark-setup.git && cd spark-setup
sudo ./bootstrap.sh michal
git config --global user.name "…" && git config --global user.email "…" && git config --global pull.rebase true
cp .env.example .env && chmod 600 .env   # HF_TOKEN
docker pull nvcr.io/nvidia/vllm:26.09-py3
make models SET=b && make models SET=d && make models SET=a
make drop-caches
make up-ui SET=b
make status && make test && make bench
```

### 4.4 Podział ról maszyn (docelowo)

```
Analitycy (przeglądarka)
        │
        ▼
Serwer aplikacyjny (VM w środowisku dev)
  ├─ aplikacja SOFA (playground)
  ├─ Open WebUI (opcjonalnie, do testów)
  └─ baza wyników, logi zapytań, użytkownicy
        │  API zgodne z OpenAI
        ▼
DGX Spark: tylko inferencja (vLLM, embeddingi)
```

| Element | Teraz | Docelowo |
|---|---|---|
| vLLM, embeddingi | Spark | Spark |
| Open WebUI | Spark (profil `ui`, dane w `/data/volumes/open-webui`; połączenia :8000, :8002, :8003, :8004) | serwer aplikacyjny; zmiana adresów połączeń |
| Aplikacja SOFA | — | serwer aplikacyjny |
| OpenCode | Mac (klient przez tunel; Coder-Next w zestawie D) | Mac każdego członka zespołu; wspólny endpoint za reverse proxy z kluczami API |

Zysk: reset lub wymiana Sparka nie kasuje historii, kont ani logów; HTTPS i logowanie zapewnia standardowa infrastruktura.

## 5. Zestawy modeli

Pamięć: vLLM widzi 121,69 GiB; w praktyce suma przydziałów ≤ ~0.85 (sekcja 3.3).

### 5.1 Modele

| Model | Architektura | Wagi w pamięci | Decode | Licencja | Rola |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B NVFP4 | MoE, 3 mld aktywnych, uwaga hybrydowa | **19,55 GiB** | **71–79 tok/s** | Apache 2.0 | szybki czat, agent, routing |
| Qwen3.8-27B NVFP4 | dense, uwaga hybrydowa | **19,08 GiB** | **12,4–13,0 tok/s** | Apache 2.0 (wg HF) | text-to-SQL, ocena wymagań (PL) |
| Gemma 4 26B-A4B NVFP4 | MoE, ~4 mld aktywnych | **17,08 GiB** | **28,8–31,1 tok/s** | Apache 2.0 | model ogólny spoza Qwena (tematy pomijane przez Qwen) |
| gpt-oss-120b (MXFP4) | MoE, 5,1 mld aktywnych | **66,14 GiB** | **34–39 tok/s** | Apache 2.0 | porównanie z Qwen (jakość, tool calling) |
| Qwen3-Coder-Next NVFP4 | MoE, 3 mld aktywnych, uwaga hybrydowa | ~43 GiB (wg autora wariantu GB10) | niezmierzony | Apache 2.0 (wg HF) | agent programistyczny (OpenCode) |
| bge-m3 | embedding | **1,06 GiB** | — | MIT | RAG |
| Qwen3.6-35B-A3B FP8 | jak wyżej | **33,64 GiB** (2026-10-13) | **47–52 tok/s** (3.9) | Apache 2.0 | zestaw C |
| Qwen3.8-27B FP8, Qwen3-Coder-Next FP8 | jak wyżej | ~28 / ~75 GiB | — | Apache 2.0 | pobrane, poza zestawami (za duże obok innych modeli) |

Wartości pogrubione: zmierzone 2026-10-11.

### 5.2 Zestawy (w repo: `profiles/set-*.env`)

| Zestaw | Porty i modele | Przydziały | Suma | Kiedy | Stan |
|---|---|---|---|---|---|
| **B: SOFA** | :8000 Qwen3.6-35B-A3B + :8002 Qwen3.8-27B + :8004 Gemma 4 26B-A4B (NVFP4) + :8001 bge-m3 | 0.25 / 0.30 / 0.24 / 0.03 | 0.82 | praca nad SOFA | **zweryfikowany**: cache 7,9 / 12,5 / 12,8 GiB; przy testach z analitykami Gemmę wyłączyć (usunąć `vllm-8004` z `COMPOSE_PROFILES`) |
| **D: kod** | :8003 Qwen3-Coder-Next + :8000 Qwen3.6-35B-A3B (NVFP4) + :8001 bge-m3 | 0.47 / 0.22 / 0.03 | 0.72 | praca z kodem w OpenCode | Coder-Next niezmierzony |
| **A: gpt-oss** | :8000 gpt-oss-120b + :8001 bge-m3 | 0.66 / 0.03 | 0.69 | porównanie z zestawem B (ten sam test, przełączenie zestawu) | **zweryfikowany**: cache 7,0 GiB (3.5) |
| **C: lekki start** | :8000 Qwen3.6-35B-A3B FP8 + :8001 bge-m3 | 0.55 / 0.06 | 0.61 | test łańcucha | **zmierzony 2026-10-13**: cache 29,5 GiB, decode 47–52 tok/s (3.9) |

Przełączanie zestawów: `make down && make drop-caches && make up-ui SET=x` (ok. 5–15 min ładowania). Usługi startują po kolei: `vllm-8000` → `embed-8001` → `vllm-8002` → `vllm-8004` (`vllm-8003` po `embed-8001`).

Niezalecane: Qwen3-Coder-Next obok dwóch innych dużych modeli (3.3); gpt-oss-120b + Qwen3-Coder-Next (~110 GiB wag).

### 5.3 Podział ról

| Rola | Model | Zestaw | Uwagi |
|---|---|---|---|
| Czat interaktywny, routing, tool calling | Qwen3.6-35B-A3B | B, D | ~79 tok/s, TTFT RAG 25k ~5 s (3.4) |
| Text-to-SQL, ocena jakości wymagań (PL) | Qwen3.8-27B | B | ~12,6 tok/s — zadania, gdzie jakość ważniejsza niż czas |
| Tematy pomijane przez Qwen, drugi punkt widzenia | Gemma 4 26B-A4B | B | ~30 tok/s, TTFT RAG 25k ~4,4 s (3.4); powód dodania: 3.6 |
| Porównanie z innym dostawcą modelu | gpt-oss-120b | A | ten sam zestaw testowy co B; 2× wolniejszy od Qwen3.6 (3.5) |
| Agent programistyczny (OpenCode) | Qwen3-Coder-Next | D | OpenCode na Macu, model na Sparku; `small_model` = Qwen3.6 |
| Embeddingi | bge-m3; docelowo Qwen3-Embedding | wszystkie | — |

## 6. Zalecenia

### 6.1 Kolejność

Przeniesiona do [`backlog.md`](backlog.md) (sekcja „Kolejność kroków”).

### 6.2 vLLM na Sparku

| Zalecenie | Uzasadnienie |
|---|---|
| Wagi w FP8, NVFP4 lub AWQ (gpt-oss: natywny MXFP4); przy kilku modelach naraz NVFP4 | vLLM słabo obsługuje GGUF; NVFP4 ma wsparcie sprzętowe w Blackwellu i zostawia miejsce na kolejne modele |
| Najwyżej trzy modele ~20 GiB albo jeden duży + jeden mały naraz | 3.3: Coder-Next obok dwóch innych modeli nie mieści się |
| Przydział instancji ≥ wagi + 1–8 GiB + cache; suma ≤ ~0.85; 1.0 = 121,69 GiB | rozmiar wag nie wystarcza do planowania (3.3) |
| Zawsze ustawiać `--max-num-seqs` jawnie (16 dla jednej osoby; wyżej dla wielu użytkowników, sekcja 6.5) | domyślne 256 przy modelach hybrydowych przekracza liczbę bloków Mamba i blokuje start (3.2) |
| Po każdym starcie odczytać `Available KV cache memory` (`make errors`) | weryfikacja przydziału; wartość ujemna = model się nie uruchomi |
| Start instancji po kolei (healthcheck + `depends_on`); `make up` uruchamiać w `tmux` i nie przerywać | instancje nie walczą o pamięć przy starcie; przerwanie zostawia kontenery w stanie `Created` |
| `make drop-caches` przed `make up` po dużych pobraniach i przed dokładaniem modelu do działającego zestawu | pamięć zunifikowana zajęta przez cache stron obniża wolną pamięć sprawdzaną przez vLLM |
| `--enable-auto-tool-choice` + `--tool-call-parser` właściwy dla modelu (Qwen: `qwen3_coder`, Gemma: `gemma4`, gpt-oss: `openai`) | wymagane przez OpenCode i narzędzia SOFA |
| Kontekst ≥ 64k dla modeli agentowych (Coder-Next: 64k) | agent szybko zbiera dziesiątki tysięcy tokenów |
| Prefix caching włączony | zmierzone przyspieszenie TTFT 9–55× przy ~25k tokenów (3.4, 3.5) |
| Parser rozumowania (`--reasoning-parser`) | rozumowanie w osobnym polu; łatwe usuwanie z historii |
| Porty tylko na `127.0.0.1` | dostęp wyłącznie przez tunel SSH lub reverse proxy |
| Nazwy usług i kontenerów po portach i modelach | komunikaty błędów i `docker ps` od razu wskazują model |
| Rzadko przełączać zestawy | start zestawu 10–15 min (3.7) |

### 6.3 OpenCode

- Uruchamiany na Macu, w repozytorium z kodem; Spark służy wyłącznie jako endpoint modelu przez tunel.
- Model: Qwen3-Coder-Next NVFP4 na :8003 (zestaw D), `small_model` (drobne zadania, tytuły sesji) Qwen3.6-35B-A3B na :8000. Lokalnie na Macu M4 Pro 48 GB Coder-Next się nie mieści.
- Konfiguracja: dostawcy zgodni z API OpenAI (`localhost:8003`, `:8000`, `:8002`, `:8004`); wzór w `clients/opencode.json.example` (z limitami kontekstu i odpowiedzi dla każdego modelu).
- Przy pracy nad SOFA (zestaw B) Coder-Next nie działa; OpenCode można wtedy przełączyć na Qwen3.6 (:8000).
- Wzór domyślnie ustawia zestaw D. Przy innym zestawie zmienić w `~/.config/opencode/opencode.json` pola `model` i `small_model` — oba muszą wskazywać model, który działa (inaczej tytuły sesji i drobne zadania kończą się błędem). Limity kontekstu w `limit.context` odpowiadają `*_MAX_LEN` z profili.

| Zestaw | `model` | `small_model` |
|---|---|---|
| D | `spark-coder/qwen3-coder-next-nvfp4` | `spark/qwen3.6-35b-a3b-nvfp4` |
| C | `spark/qwen3.6-35b-a3b` | `spark/qwen3.6-35b-a3b` |
| B | `spark/qwen3.6-35b-a3b-nvfp4` | `spark/qwen3.6-35b-a3b-nvfp4` |
| A | `spark/gpt-oss-120b` | `spark/gpt-oss-120b` |

- Tool calling na zestawie C sprawdzony 2026-10-13 przez API (`curl` z narzędziem `read_file`): `finish_reason: tool_calls`, poprawne argumenty; parser `qwen3_coder` działa.

### 6.4 Sieć i bezpieczeństwo

| Zalecenie | Uzasadnienie |
|---|---|
| Spark na kablu (zrobione); docelowo mesh z przewodowym backhaulem zamiast repeatera | repeater obcina przepustowość i daje skoki opóźnień |
| mDNS (`spark-28e3.local`) wystarcza w domu; w sieci firmowej IP lub DNS od IT | mDNS bywa blokowany w sieciach firmowych |
| `dai-coe` zachować jako konto awaryjne (lokalnie); SSH tylko dla `michal` | ograniczenie powierzchni ataku |
| Wyłączyć logowanie hasłem przez SSH dopiero po potwierdzeniu działania klucza | ryzyko odcięcia dostępu |
| Tailscale / dostęp spoza sieci tylko po uzgodnieniu z IT | sprzęt służbowy, dane niejawne |

### 6.5 Konfiguracja dla wielu użytkowników (testy analityków)

Obecne profile (`--max-num-seqs 16`) są ustawione pod jedną osobę. Przed udostępnieniem playgroundu analitykom trzeba je przestawić i zmierzyć pod obciążeniem. Punktem wyjścia jest zestaw B **bez Gemmy** (Qwen3.6 + Qwen3.8 + bge-m3, suma 0.58), który zostawia ~0.27 zapasu na większe przydziały.

#### Parametry vLLM, które decydują o pracy wielu użytkowników

| Parametr | Co robi | Wpływ na pamięć | Wartość: jedna osoba → analitycy |
|---|---|---|---|
| `--max-num-seqs` | maks. liczba zapytań przetwarzanych jednocześnie przez instancję; nadmiarowe czekają w kolejce | modele hybrydowe: 1 blok stanu Mamba na sekwencję (stały rozmiar); wszystkie modele: większe grafy CUDA | 16 → 32–64 |
| `--max-model-len` | maks. długość kontekstu jednego zapytania | KV cache rośnie z sumą tokenów wszystkich równoczesnych zapytań | 32–64k → 16–32k (RAG z rerankerem i zapytania strukturalne mieszczą się w kilku–kilkunastu tys. tokenów) |
| `--gpu-memory-utilization` | ile pamięci rezerwuje instancja (wagi + grafy + cache) | bezpośrednio | większy przydział dla modelu obsługującego analityków |
| `--kv-cache-dtype fp8` | KV cache w FP8 zamiast BF16 | ~2× więcej tokenów w tej samej pamięci | włączone |
| `--enable-prefix-caching` | wspólny początek promptu (system prompt, schemat EA, narzędzia) liczony raz dla wszystkich | oszczędza prefill i pamięć | włączone; prompt budować wg `context/sofa-obserwacje.md` sekcja 8 |
| `--enable-chunked-prefill`, `--max-num-batched-tokens` | dzieli długie prefille na kawałki, żeby jedno zapytanie RAG nie blokowało pozostałych; mniejsza wartość = mniejszy szczyt aktywacji przy starcie | — | włączone; `max-num-batched-tokens` 4096–8192 |
| `--scheduling-policy priority` (opcjonalnie) | zapytania z wyższym priorytetem obsługiwane przed innymi | — | czat analityka przed oceną wsadową na tej samej instancji |

Zasada szacowania:

```
pamięć instancji ≈ wagi + ~1–8 GiB (grafy CUDA, aktywacje, bufory)
                 + max_num_seqs × stan Mamba na sekwencję        (modele hybrydowe)
                 + suma tokenów równoczesnych zapytań × KV na token
```

Punkty odniesienia z pomiarów (3.2–3.6): Qwen3.6-35B-A3B NVFP4: przy ~26 GiB cache 3,8–4,2 GiB (~190 bloków Mamba), przy ~30 GiB cache 7,9 GiB. Qwen3.8-27B NVFP4: przy ~24 GiB cache −3,0 GiB, przy ~36,5 GiB cache 11,7–12,5 GiB. Gemma 4 przy ~29 GiB cache 12,8 GiB. Pojedynczy użytkownik: prefill Qwen3.6 ~5 000 tok/s, Qwen3.8 ~2 200 tok/s — przy N równoczesnych długich promptach RAG czas do pierwszego tokena rośnie mniej więcej liniowo z N (prefill dzielony między zapytania).

vLLM wypisuje przy starcie linie `Available KV cache memory: … GiB` i `Maximum concurrency for … tokens per request: …x` — to bezpośrednia odpowiedź, ilu równoczesnych zapytań o danej długości instancja obsłuży. Odczytać przez `make errors` lub `make log P=8000` i wpisać do tabeli pomiarów.

#### Ile `max_num_seqs` potrzeba

| Scenariusz | Liczba równoczesnych zapytań | Proponowane `max_num_seqs` |
|---|---|---|
| Jedna osoba, OpenCode / czat | 1–4 (agent może wysyłać kilka naraz) | 16 |
| Playground, 5–10 analityków | zwykle 2–5 naraz (ludzie czytają odpowiedzi), szczyty przy wspólnych sesjach | 32 |
| Warsztat / demo, 10–20 osób naraz | 10–20 | 32–64 |
| Ocena wsadowa wymagań (warstwa 2 analizy braków) | tyle, ile się zmieści; liczy się przepustowość, nie czas pojedynczej odpowiedzi | 64–128 na osobnej instancji lub poza godzinami pracy |

Za mała wartość nie powoduje błędów, tylko kolejkę: zapytania czekają, rośnie czas do pierwszego tokena. Za duża wartość zabiera pamięć na stan, który i tak nie zostanie wykorzystany, albo blokuje start (3.2). Gdy KV cache się zapełni, vLLM wstrzymuje część zapytań i przelicza je później (wydłużony czas odpowiedzi, nie błąd).

#### Proponowany profil dla testów analityków (`set-analysts`, do dodania w repo na bazie zestawu B)

| Usługa | Model | `GPU_MEM` | `MAX_LEN` | `max_num_seqs` | Uwagi |
|---|---|---|---|---|---|
| `vllm-8000` | Qwen3.6-35B-A3B NVFP4 | ~0.40–0.45 | 32768 | 32 | model obsługujący wszystkich analityków: czat, routing, tool calling |
| `embed-8001` | bge-m3 | 0.03–0.04 | 8192 | domyślnie | embeddingi RAG są lekkie |
| `vllm-8002` | Qwen3.8-27B NVFP4 | ~0.32–0.35 | 16384 | 8–16 | text-to-SQL / ocena jakości; mniej równoczesnych zapytań, bo wolniejszy (gęsty, ~12,6 tok/s) |

Suma ~0.75–0.84. Wartości do potwierdzenia pomiarem (`Maximum concurrency` w logu startu).

Zasady:
- Na czas testów z analitykami nie uruchamiać Gemmy ani zestawu D (Coder-Next); OpenCode wtedy przez Qwen3.6 albo poza godzinami testów.
- Ocena wsadowa i interaktywny czat na osobnych instancjach albo z `--scheduling-policy priority`, żeby wsad nie wydłużał odpowiedzi analitykom.
- Jedna instancja obsługująca wszystkich wykorzystuje prefix caching najlepiej (wspólny system prompt i schemat EA liczone raz).
- Modele MoE z małą liczbą aktywnych parametrów (Qwen3.6, Gemma 4, gpt-oss) skalują się na wielu użytkowników znacznie lepiej niż gęsty Qwen3.8-27B.

#### Pomiar przed udostępnieniem

| Krok | Narzędzie | Co zapisać |
|---|---|---|
| 1. Pojemność z logu startu | `make errors` | `Available KV cache memory`, `Maximum concurrency` dla 16k i 32k |
| 2. Test współbieżności | rozszerzyć `bench/run_bench.py` o równoległe zapytania (1, 4, 8, 16, 32 naraz) albo `vllm bench serve` z obrazu vLLM | TTFT p50/p95, tok/s na użytkownika, łączna przepustowość |
| 3. Kolejka i zajętość cache w trakcie | endpoint `/metrics` vLLM (Prometheus): liczba zapytań w trakcie i czekających, zajętość KV cache | czy zapytania czekają; czy cache dochodzi do 100% |
| 4. Scenariusze SOFA | zapytania typowe dla analityków: krótkie (ścieżka strukturalna, text-to-SQL) i długie (RAG 8–16k) | osobno TTFT dla każdego typu (por. `context/sofa-obserwacje.md` sekcja 11) |
| 5. Decyzja | — | `max_num_seqs`, `MAX_LEN`, `GPU_MEM` dla profilu `set-analysts`; wynik do wniosku o Sparka (ilu analityków obsłuży jedno urządzenie) |

Kryterium akceptacji (propozycja do uzgodnienia): przy przewidywanej liczbie równoczesnych analityków TTFT p95 dla zapytań strukturalnych < 3 s i dla RAG 16k < 15 s, bez wstrzymywania zapytań przez brak KV cache. Dla jednego użytkownika spełnione dla wszystkich zmierzonych modeli (3.4, 3.5).

### 6.6 Backlog

Przeniesiony do [`backlog.md`](backlog.md).

## 7. Obraz odzyskiwania

| Parametr | Wartość |
|---|---|
| Plik | `dgx-spark-recovery-image-1.145.33.tar.gz` |
| Wersja | 1.145.33 |
| SHA-256 | `bed374059bfbab1587698da972ae9948280ea4b75e56e3bcb89fdbf378fcc8d8` |
| Źródło | https://www.nvidia.com/en-us/drivers/dgx-spark-recovery-software/ |
| Data pobrania | 2026-10-11 |
| Nośnik | pendrive SanDisk 125 GB, przygotowany 2026-10-11 na macOS skryptem `CreateUSBKeyMacOS.sh` (wynik: `SUCCESSFULLY FLASHED`) |

Weryfikacja sumy kontrolnej:

```bash
shasum -a 256 dgx-spark-recovery-image-1.145.33.tar.gz
```

## 8. Przygotowanie pendrive'a (macOS)

Wymagania: pendrive ≥ 16 GB (cała zawartość zostanie usunięta), uprawnienia administratora.

1. Pobrać archiwum ze strony NVIDIA (sekcja 7) i zweryfikować SHA-256.
2. Rozpakować:
   ```bash
   tar -xzf dgx-spark-recovery-image-1.145.33.tar.gz
   ```
3. Zidentyfikować pendrive (nie pomylić z dyskiem wewnętrznym ani z zamontowanymi obrazami dysków):
   ```bash
   diskutil list external
   ```
4. Odmontować ewentualne obrazy dysków z pendrive'a (np. `hdiutil detach /dev/diskN`).
5. Uruchomić skrypt i wskazać pendrive:
   ```bash
   cd usbimg.customer
   sudo bash CreateUSBKeyMacOS.sh
   ```
6. Odpowiedniki dla innych systemów: `CreateUSBKey.sh` (Linux), `CreateUSBKey.cmd` (Windows, jako administrator).

## 9. Procedura odzyskiwania na DGX Spark

Uwaga: odzyskiwanie całkowicie kasuje wewnętrzny SSD i przywraca system oraz firmware do stanu fabrycznego. Przed rozpoczęciem zabezpieczyć dane.

1. Odłączyć od Sparka wszystkie zewnętrzne nośniki danych.
2. Podłączyć pendrive odzyskiwania do portu USB Sparka oraz klawiaturę **na kablu USB bezpośrednio do Sparka** (klawiatury Bluetooth mogą nie działać).
3. Włączyć urządzenie, przytrzymując **Esc** lub **Del**, aby wejść do UEFI.
4. Przywrócić domyślne ustawienia UEFI:
   - **Save & Exit → Restore Defaults → Yes** („Load Optimized Defaults”),
   - **Save Changes and Reset**,
   - podczas restartu ponownie przytrzymać **Esc** / **Del**.
5. Uruchomić z pendrive'a: **Save & Exit → Boot Override →** wybrać pendrive → **Enter**.
   - Jeśli pendrive jest widoczny, ale system uruchamia się z dysku: **Security → Secure Boot → Disabled**, zapisać, wejść ponownie do UEFI i powtórzyć Boot Override. Po zakończeniu odzyskiwania Secure Boot włącza się automatycznie.
6. W środowisku odzyskiwania:
   - ekran powitalny: **Enter** = dalej, **Esc** = anuluj,
   - ekran ostrzeżenia: **[EXIT]** = restart bez zmian, **[START RECOVERY]** = reflash SSD,
   - obserwować ekran postępu; po zakończeniu przejrzeć wynik i potwierdzić,
   - na ekranie końcowym **Enter** = restart.
7. Po restarcie przejść konfigurację początkową (OOBE) i założyć własne konto.
8. Odtworzyć środowisko z repozytorium `spark-setup` (sekcja 4.3); na Macu usunąć stary klucz hosta: `ssh-keygen -R spark-28e3.local`. Czas pobrania modeli i obrazu: sekcja 3.1; start zestawu: sekcja 3.7. Po odtworzeniu ponownie założyć konto administratora Open WebUI, jeśli `/data/volumes` nie było w kopii zapasowej.

Test nośnika bez kasowania danych: wejść do UEFI i użyć **USB OS Recovery Drive Validation** albo uruchomić pendrive przez Boot Override i anulować (**Esc**) na ekranie powitalnym.

## 10. Rozwiązywanie problemów

| Problem | Działanie |
|---|---|
| UEFI nie widzi pendrive'a | inny port, inny pendrive; unikać hubów i stacji dokujących |
| Pendrive widoczny, ale start z SSD | wyłączyć Secure Boot (sekcja 9, krok 5) |
| Klawiatura nie działa w UEFI | zwykła klawiatura USB podłączona bezpośrednio |
| Błąd zapisu przy tworzeniu nośnika na komputerze służbowym | możliwa blokada polityk DLP/IT; użyć innego komputera lub zgłosić do IT |
| Problemy z konkretną wersją obrazu | sprawdzić forum NVIDIA; poprzednie wersje bywają dostępne pod bezpośrednimi linkami |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` po resecie | `ssh-keygen -R spark-28e3.local` na Macu |
| `spark-28e3.local` nie odpowiada | `systemctl status avahi-daemon` na Sparku; ta sama sieć; wyłączyć VPN; awaryjnie IP (`hostname -I`) |
| `curl localhost:800X`: `Couldn't connect … after 0 ms` | na Macu nie ma tunelu dla tego portu: sprawdzić `ssh -G spark \| grep -i localforward`; po zmianie `~/.ssh/config` zamknąć i ponownie otworzyć `ssh -N spark` |
| `git push` / `git clone`: `Permission denied (publickey)` | dodać klucz publiczny Maca na GitHubie (Settings → SSH keys); na Sparku łączyć się przez `ssh -A spark` |
| `git commit`: `Author identity unknown` | `git config --global user.name …` i `user.email …` |
| `git pull`: `divergent branches` | `git pull --rebase`; na stałe `git config --global pull.rebase true` |
| Komentarze `#` w zsh na Macu traktowane jako argumenty | wklejać polecenia bez komentarzy albo `setopt interactive_comments` w `~/.zshrc` |
| Edytor (Cursor) nie pokazuje zmian po `git am` / `git pull` | sprawdzić `git log`; przeładować okno (Cmd+Shift+P → Reload Window) |
| `make up`: `dependency … failed to start`, kontener restartuje się w pętli | `make errors` albo `docker logs <kontener> 2>&1 \| grep -E "Error:\|GiB"`; zatrzymać pętlę: `make down` lub `docker stop <kontener>` |
| Kontener w stanie `Created`, pusty log (np. po przerwaniu `make up`) | `docker start <kontener>`; jeśli nie pomaga: `docker rm <kontener>` i `make up-ui SET=x` (`backlog.md` B4) |
| `make errors` pokazuje stare błędy kontenera spoza bieżącego zestawu | usunąć zatrzymany kontener: `docker rm <kontener>` |
| `max_num_seqs (256) exceeds available Mamba cache blocks` | ustawić `--max-num-seqs` (np. 16) albo zwiększyć `*_GPU_MEM` (sekcja 3.2) |
| `Available KV cache memory: -X GiB` / `No available memory for the cache blocks` | zwiększyć `*_GPU_MEM` danego modelu o co najmniej X GiB + zapas na kontekst; jeśli suma przekracza ~0.85 — mniej modeli w zestawie (sekcja 3.3) |
| `Free memory on device … is less than desired GPU memory utilization` | `make drop-caches`; potem mniejszy przydział lub mniej modeli w zestawie (3.3) |
| vLLM: OOM przy starcie | `make drop-caches`, potem mniejsze `*_GPU_MEM` / `*_MAX_LEN` |
| Open WebUI nie pokazuje nowego modelu / endpointu | połączenia są zapisane w bazie Open WebUI: dodać w Administrator → Ustawienia → Połączenia (adres `http://vllm-800X:8000/v1`, klucz `none`); na stałe `backlog.md` B1 |
| Open WebUI: `KeyError: 'Session not found'` w logu | odświeżyć kartę przeglądarki; nieszkodliwe |
| Model Qwen odmawia tematów politycznych dotyczących Chin | użyć Gemmy (:8004) lub gpt-oss (zestaw A) (3.6) |

## 11. Źródła

- System Recovery — DGX Spark User Guide: https://docs.nvidia.com/dgx/dgx-spark/system-recovery.html
- DGX Spark System Recovery Image: https://www.nvidia.com/en-us/drivers/dgx-spark-recovery-software/
- NGC vLLM container: https://catalog.ngc.nvidia.com/orgs/nvidia/containers/vllm
- Gemma 4 26B-A4B NVFP4: https://hf.co/nvidia/Gemma-4-26B-A4B-NVFP4
- Założenia modeli i platform: `context/llm-pamiec-wzor.md`, `context/sofa-obserwacje.md`, symulator `context/rag-ea-symulator.html`
- Wyniki pomiarów: repozytorium `spark-setup`, katalog `bench/results/`
