# Backlog i stan prac

Jedno miejsce na to, co zostało do zrobienia. Szczegóły i uzasadnienia: [`findings.md`](findings.md), decyzje: [`decisions.md`](decisions.md), czas pracy: [`czas-pracy.md`](czas-pracy.md).

## Stan na 2026-10-11 (gdzie skończyliśmy)

- Spark: konto `michal`, klucz SSH, `/data/hf`, wszystkie modele pobrane, obraz vLLM `nvcr.io/nvidia/vllm:26.09-py3`.
- Działa zestaw B: :8000 Qwen3.6, :8002 Qwen3.8, :8004 Gemma 4, :8001 bge-m3, Open WebUI :8080 (Gemma dodana w panelu ręcznie).
- Zmierzone (`make bench`): Qwen3.6, Qwen3.8, Gemma 4 (zestaw B), gpt-oss-120b (zestaw A); wyniki JSON w `bench/results/` zacommitowane, liczby w `findings.md` 3.4–3.6.
- Dostęp z Maca wyłącznie przez tunel `ssh -N spark` (porty 8000–8004, 8080).

## Plan na 2026-10-12

| Kolejność | Zadanie | Odnośniki |
|---|---|---|
| 1 | Praca z OpenCode na **zestawie C** (`make up SET=c`: Qwen3.6-35B-A3B FP8 na :8000 + bge-m3): sprawdzenie całego łańcucha (tunel, konfiguracja klienta, tool calling) i pomiar zestawu C — **zrobione 2026-10-13**: pomiar (`findings.md` 3.9), OpenCode 1.19.0 działa (3.10) | `findings.md` 6.3, 5.2; `clients/opencode.json.example`; ustawienia `model` / `small_model` dla zestawu C: `findings.md` 6.3 |
| 2 | Scenariusze SOFA na modelach zestawu B: ocena jakości wymagań, text-to-SQL, RAG nad modelem EA, pytania z obszaru geopolityki | krok 11; `findings.md` 3.6; `docs/context/sofa-obserwacje.md` |
| 3 | Dyskusja: jak zmienić konfigurację pod pracę wieloużytkownikową — profil `set-analysts`, `max_num_seqs`, przydziały pamięci, limity kontekstu, test współbieżności | krok 13, B11; `findings.md` 6.5 |

## Najbliższe drobne kroki

| Zadanie | Polecenie / uwagi |
|---|---|
| Powtórzyć test tematyczny: oba sformułowania („ile osób zginęło”, „co się wydarzyło”) na :8000, :8002, :8004 i gpt-oss | notować treść pytania razem z odpowiedzią; wynik do `findings.md` 3.6 |
| Komentarz w `profiles/set-b.env` przy Gemmie („NIEZMIERZONE”) | zaktualizować o pomiar: wagi 17,08 GiB, cache 12,77 GiB przy 0.24 |
| `poc_output.md` w projekcie claude.ai | oznaczyć jako archiwum, wskazać repo jako źródło prawdy |

## Kolejność kroków

| Krok | Działanie | Status |
|---|---|---|
| 1 | Założyć repo `spark-setup`; przenieść do `bootstrap.sh` kroki z `findings.md` 3 | zrobione |
| 2 | Podłączyć Sparka kablem do routera | zrobione |
| 3 | Pobrać modele; uruchomić zestaw B | zrobione (poprawki `findings.md` 3.2, 3.3) |
| 4 | Zweryfikować zestaw B (`make status`, `make errors`, tunel z Maca, `make bench`) | zrobione (`findings.md` 3.3, 3.4) |
| 5 | Zestaw A: pamięć i wydajność gpt-oss-120b | zrobione (`findings.md` 3.5) |
| 6 | Open WebUI | zrobione (`findings.md` 3.8) |
| 7 | Gemma 4 w zestawie B: start, pamięć, wydajność i test tematyczny | zrobione (`findings.md` 3.6, pomiary 3.4) |
| 8 | Zaktualizować symulator: efektywne TFLOPS i decode zależne od modelu (`findings.md` 3.5) | zrobione 2026-10-13 (Spark z pomiarów, dodana Gemma 4) |
| 9 | Uruchomić zestaw D, podłączyć OpenCode na Macu, zmierzyć pamięć i wydajność Coder-Next | do zrobienia |
| 10 | Potwierdzić licencje Qwen3.8 i Qwen3-Coder-Next w plikach LICENSE (tagi HF: Apache 2.0) | do zrobienia |
| 11 | Zestaw testowy SOFA na Qwen3.8, gpt-oss i Gemmie (w tym pytania z obszaru geopolityki, `findings.md` 3.6) | do zrobienia |
| 12 | Przypiąć rewizje modeli (`make pin`) po udanym teście | do zrobienia |
| 13 | Test obciążeniowy pod wielu użytkowników i profil `analysts` (`findings.md` 6.5) | do zrobienia przed udostępnieniem analitykom |
| 14 | Dokończyć zabezpieczenia z `findings.md` 2.3 (SSH, ufw, telemetria, usługi, Wi-Fi) | do zrobienia |
| 15 | Przy udostępnianiu zespołowi: reverse proxy z HTTPS i kluczami API; UI na serwer aplikacyjny | później |

## Backlog

Zmiany zidentyfikowane, celowo jeszcze niewprowadzone. Numeracja B* jest stała (odwołania w `findings.md`); nowe pozycje dopisywać na końcu, zrobione oznaczać w kolumnie priorytetu, nie usuwać.

| Nr | Obszar | Zadanie | Uzasadnienie | Priorytet |
|---|---|---|---|---|
| B1 | Open WebUI | `ENABLE_PERSISTENT_CONFIG=false` w `compose.yaml` — połączenia zawsze z `OPENAI_API_BASE_URLS` | `findings.md` 3.8: nowy endpoint (:8004) nie pojawił się automatycznie; konfiguracja w repo zamiast w bazie UI. Wada: zmiany z panelu administratora nie przetrwają restartu | średni |
| B2 | vLLM | Trwały cache kompilacji: wolumen `/data/volumes/vllm-cache` → `/root/.cache` w kontenerach vLLM | `findings.md` 3.7: kompilacja i profilowanie 25–80 s na model powtarzane przy każdym starcie | wysoki |
| B3 | vLLM | Test `--load-format fastsafetensors` na jednym modelu | `findings.md` 3.7: wczytanie wag ~130–150 MB/s; NVIDIA używa tej opcji w konfiguracji Qwen3.6 NVFP4 dla DGX Spark; wymaga pakietu w obrazie | średni |
| B4 | Makefile | `make up` odporne na przerwanie (start w tle, dokończenie przez `docker start` kontenerów w stanie `Created`) | `make up` przerwane w trakcie czekania zostawiło Gemmę w stanie `Created`; ponowne `make up` jej nie uruchomiło w podsumowaniu | średni |
| B5 | Makefile | `make errors` bez kontenera Open WebUI (albo z osobnym filtrem) | komunikaty `KeyError: 'Session not found'` mieszają się z błędami modeli | niski |
| B6 | Profil B | Gemma 0.24 → ~0.20, zwolnioną pamięć oddać Qwen3.6 (najmniej cache: 7,9 GiB) | `findings.md` 3.6: Gemma ma 12,8 GiB cache, najwięcej w zestawie | niski |
| B7 | bootstrap.sh | `git config` (user.name, user.email, `pull.rebase true`) dla użytkownika | ustawione ręcznie; znikną po resecie | niski |
| B8 | ssh | Tunel 8004 w `ssh/config.example` (plik utrzymywany ręcznie) — sprawdzić, czy dopisany i wypchnięty | `findings.md` 4.1 | niski |
| B9 | Open WebUI | Przypięcie wersji obrazu zamiast `:main`; nazwy i opisy modeli; embeddingi dokumentów przez bge-m3 (`http://embed-8001:8000/v1`); wariant modelu bez trybu myślenia do prostych pytań; po teście: modele publiczne, rejestracja z zatwierdzaniem | wygoda i powtarzalność; przygotowanie pod analityków | niski |
| B10 | Sposób pracy | Przeniesienie pracy do repozytorium i Cursor / Claude Code: `docs/` (findings, decisions, backlog, context), `AGENTS.md` + `CLAUDE.md`, komenda `/finding` | dokumentacja obok kodu, wersjonowana, dostępna agentowi | **zrobione 2026-10-11** (commit „Move findings, decisions and backlog into the repo”); do zrobienia: oznaczyć `poc_output.md` w projekcie claude.ai jako archiwum |
| B11 | bench | Test współbieżności (1–32 równoczesnych zapytań) i profil `set-analysts` | `findings.md` 6.5 | wysoki przed testami z analitykami |
| B12 | symulator (`docs/context/rag-ea-symulator.html`) | Efektywne TFLOPS i decode zależne od modelu (MoE ~30–55, dense ~110–130 TFLOPS; decode zmierzony) | `findings.md` 3.5 | **zrobione 2026-10-13**: dla Sparka TTFT i decode interpolowane z `bench/results/`, wagi zmierzone, Gemma 4 dodana; pozostałe platformy nadal szacunki |
| B13 | modele | `make pin` — przypięcie rewizji wszystkich modeli z działających zestawów | odtwarzalność po resecie | średni |
| B14 | compose / odtwarzalność | Sprawdzić zachowanie zestawu B po reboocie Sparka; jeśli start równoległy kończy się OOM — zdjąć `restart: unless-stopped` z usług vLLM albo uruchamiać je jednostką systemd wołającą `make up SET=b` | wszystkie kontenery mają `restart: unless-stopped`, a `docker` jest `enabled`, więc po reboocie trzy instancje vLLM startują **równolegle**, bez kolejności wymuszanej przez `depends_on` + healthcheck w `make up`. Przy sumie 0.82 i spadku wolnej pamięci do ~14,7 GiB przy ładowaniu sekwencyjnym (`findings.md` 3.6) może to skończyć się OOM i pętlą restartów. Nieprzetestowane — Spark z działającym zestawem B nie był jeszcze restartowany | średni |
| B15 | vLLM | Test dekodowania spekulacyjnego (MTP, `--speculative-config`) na Qwen3.6: czy model ma głowice MTP, zysk tok/s przy generowaniu kodu | jeden strumień jest ograniczony przepustowością pamięci (`findings.md` 3.9, 3.10: ~48 tok/s FP8); spekulacja może podnieść decode bez zmiany modelu — nieprzetestowane, wymaga restartu zestawu | średni → **wysoki**: na M3 Max Ollama używa MTP dla Qwen3.8 automatycznie — 39–51 tok/s wobec 21 bez MTP (`findings.md` 3.11.1); Spark 12,6 tok/s |
| B16 | OpenCode | Równoległe agenty: kilka `opencode run "…"` w osobnych `git worktree`, pomiar łącznego tok/s i czasu zadania | 2 równoczesne zapytania dały ~77 tok/s łącznie wobec ~48 dla jednego (`findings.md` 3.10); limit `--max-num-seqs 16`, cache na ~21 zapytań po 64k (3.9); powiązane z B11 | niski |
| B17 | porównanie | To samo zadanie w OpenCode na Sparku (zestaw C) i na Macu (llama.cpp, Qwen3.6 GGUF UD-Q4_K_M), zapis sesji z monitora tokenów do `bench/sessions/` | procedura i kolumny: `findings.md` 6.3.1; odpowiada na pytanie, ile daje Spark wobec laptopa w pracy agentowej, a nie tylko w `make bench` | średni |
| B18 | porównanie | Jakość modeli w pracy agentowej: to samo zadanie (np. testy Minesweepera, nowa sesja OpenCode) na Qwen3.6-35B-A3B z parametrami ogólnymi i do kodu (`temperature` 0,6, `presence_penalty` 0 — tag Ollamy `qwen3.6:35b-a3b-coding-nvfp4`) oraz Qwen3-Coder-Next (Ollama 52 GB; Spark zestaw D); miary: czas, liczba kroków, ucięte odpowiedzi, czy testy przechodzą | dotąd mierzona tylko szybkość; wybór modelu do programowania agentowego (rekomendacja robocza: Qwen3.6) wymaga oceny jakości; uzupełnia krok 9 i B17 | średni |
| B19 | OpenCode / Claude Code na Macu | Dostawca Ollamy w `clients/opencode.json.example` (`http://localhost:11434/v1`, Qwen3.6, limity kontekstu); w aplikacji Ollama kontekst ≥ 64k (domyślny ucina prompt agenta); Claude Code: `ollama launch claude --model qwen3.6:35b-a3b` (Ollama 0.40 obsługuje API Anthropic `/v1/messages`) | praca agentowa na Macu bez Sparka; Qwen3.8 na Macu tylko przy krótkim kontekście (prefill ~190 tok/s, 3.11) | średni |
