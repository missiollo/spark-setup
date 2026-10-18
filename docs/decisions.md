# Decyzje

Rejestr decyzji: co, dlaczego, jakie alternatywy odrzucono. Nowe decyzje dopisywać na końcu; zmienioną decyzję oznaczyć „zastąpiona przez D-xx” zamiast usuwać.

| Nr | Data | Decyzja | Uzasadnienie | Odrzucone alternatywy | Szczegóły |
|---|---|---|---|---|---|
| D-01 | 2026-10-11 | Reinstalacja Sparka z obrazu odzyskiwania odłożona | audyt bez śladów poprzednich PoC; system praktycznie fabryczny; nośnik odzyskiwania przygotowany i przetestowany | reset fabryczny od razu | `findings.md` 2.4 |
| D-02 | 2026-10-11 | Własne konto `michal`; `dai-coe` tylko jako konto awaryjne (hasło ustawione) | rozdzielenie konta fabrycznego od roboczego; SSH tylko dla `michal` | praca na `dai-coe` | `findings.md` 2.3, 6.4 |
| D-03 | 2026-10-11 | Adresowanie przez mDNS (`spark-28e3.local`), bez wpisów DNS / `/etc/hosts` | brak serwera DNS w domu; avahi działa od razu | stały IP, wpis w `/etc/hosts` | `findings.md` 3, 6.4 |
| D-04 | 2026-10-11 | Dostęp do usług wyłącznie przez tunel SSH; porty tylko na `127.0.0.1` | w sieci widoczny tylko port 22 z kluczem; brak uwierzytelniania w vLLM | wystawienie portów w LAN; Tailscale (wymaga zgody IT) | `findings.md` 4.1 |
| D-05 | 2026-10-11 | Wszystko w kontenerach (NGC vLLM, ARM64/CUDA 13); nic przez pip na hoście | odporność na aktualizacje DGX OS; odtwarzalność | instalacja vLLM na hoście; obrazy z Docker Hub | `findings.md` 4.3 |
| D-06 | 2026-10-11 | Modele pobierane bezpośrednio na Sparku do `/data/hf` (grupa `llm`, setgid) | szybciej niż kopiowanie z laptopa; wspólny cache dla użytkowników | kopiowanie wag z Maca | `findings.md` 4.2 |
| D-07 | 2026-10-11 | Repozytorium `spark-setup` (prywatne, GitHub) jako jedyne źródło konfiguracji: manifest modeli, profile zestawów, compose, bench | odtworzenie po resecie / na innym sprzęcie jednym ciągiem poleceń | ręczna konfiguracja | `findings.md` 4.3 |
| D-08 | 2026-10-11 | Spark na kablu do routera | Wi-Fi z repeaterem: 19–228 ms, pobieranie szacowane na godziny | Wi-Fi | `findings.md` 3.1 |
| D-09 | 2026-10-11 | Wagi NVFP4 przy kilku modelach naraz | wsparcie sprzętowe w Blackwellu; ~2× mniej pamięci niż FP8 | FP8 dla wszystkich (za mało pamięci), GGUF (słabe wsparcie w vLLM) | `findings.md` 5.1, 6.2 |
| D-10 | 2026-10-11 | Zawsze jawne `--max-num-seqs` (16; gpt-oss 32) | domyślne 256 blokuje start modeli hybrydowych (Mamba/DeltaNet) | domyślne ustawienia vLLM | `findings.md` 3.2 |
| D-11 | 2026-10-11 | Usługi i kontenery nazwane po portach (`vllm-8000`, `spark-8000-<model>`) | błąd od razu wskazuje model; `make status/log/errors` | generyczne `llm`, `llm2` | `findings.md` 3.2 |
| D-12 | 2026-10-11 | Przebudowa zestawów: B = SOFA (Qwen3.6 + Qwen3.8 + bge-m3), D = kod (Coder-Next + Qwen3.6), A = gpt-oss solo, C = lekki start | trzy duże modele z Coder-Next nie mieszczą się (KV −3 GiB); gpt-oss zajmuje 66 GiB | Coder-Next w zestawie B; gpt-oss obok Qwena | `findings.md` 3.3, 5.2 |
| D-13 | 2026-10-11 | Zasada planowania pamięci: przydział ≥ wagi + 1–8 GiB + cache; suma ≤ ~0.85; 1.0 = 121,69 GiB | zweryfikowana pomiarami na zestawach A i B | planowanie po rozmiarze wag | `findings.md` 3.3 |
| D-14 | 2026-10-11 | Gemma 4 26B-A4B NVFP4 na :8004 w zestawie B jako model ogólny spoza rodziny Qwen | Qwen unika tematów politycznych dotyczących Chin; gpt-oss odpowiada, ale wymaga osobnego zestawu | modele „uncensored” / abliterowane (niższa jakość, nieznane pochodzenie, trudne do uzasadnienia przy audycie); gpt-oss obok Qwena (brak pamięci) | `findings.md` 3.6 |
| D-15 | 2026-10-11 | Port 8003 zostaje dla Qwen3-Coder-Next | konfiguracja OpenCode (`clients/opencode.json.example`) bez zmian | Gemma na 8003 | `findings.md` 3.6 |
| D-16 | 2026-10-11 | OpenCode na Macu, model na Sparku przez tunel (`small_model` = Qwen3.6) | Coder-Next nie mieści się na M4 Pro 48 GB | OpenCode na Sparku; model lokalny na Macu | `findings.md` 6.3 |
| D-17 | 2026-10-11 | Open WebUI na razie na Sparku (profil `ui`); docelowo na serwerze aplikacyjnym | szybki start testów; Spark docelowo tylko inferencja | od razu osobny serwer | `findings.md` 4.4 |
| D-18 | 2026-10-11 | Poprawki Open WebUI (`ENABLE_PERSISTENT_CONFIG`) i usprawnienia startu odłożone do backlogu | najpierw stabilny zestaw B; obejście ręczne wystarcza | wprowadzenie od razu | `backlog.md` B1–B5 |
| D-19 | 2026-10-11 | Opcja `--safetensors-load-strategy=prefetch` nie jest używana | brak zysku (150 s vs 157 s); wąskim gardłem jest przepakowanie wag na CPU | — | `findings.md` 3.7 |
| D-20 | 2026-10-11 | Praca na dwóch maszynach przez `git pull --rebase` (`pull.rebase true`) | liniowa historia bez commitów „Merge branch” | merge | `findings.md` 4.3 |
| D-21 | 2026-10-11 | Dokumentacja przeniesiona do repo (`docs/`); źródłem prawdy jest repo, praca w Cursor / Claude Code | dokumentacja obok kodu, wersjonowana, dostępna agentowi; koniec przenoszenia poprawek przez `git am` | dalsza praca w rozmowie claude.ai | `backlog.md` B10 |
| D-22 | 2026-10-18 | Zadania oceny (np. naprawa testów `openMinesweeper`) wykonują wyłącznie modele lokalne w OpenCode; my przygotowujemy procedurę, klucz odpowiedzi, pomiar i raporty | celem PoC jest środowisko developerskie i analityczne wspierane przez LLM offline — poprawka zrobiona przez model chmurowy nie mówi nic o modelach lokalnych i psuje stan bazowy | poprawki przez Claude Code; ręczne poprawki przed oceną | `agent-eval.md` 1 |
