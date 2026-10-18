# Ocena pracy z lokalnymi modelami — metodyka i procedura

Cel: przygotować i udokumentować sposób, w jaki środowisko testowe **developerskie** (agent piszący i poprawiający kod) i **analityczne** (SOFA: jakość wymagań, RAG nad EA, text-to-SQL) jest wspierane przez LLM działające offline (Spark, Mac). Wynikiem są: procedura, miary i raporty z przebiegów, na których oprze się wybór modelu i sposobu pracy.

Powiązane: B18 (metoda), B20 (testy `openMinesweeper`), `findings.md` 3.10 (sesja OpenCode), 6.7 (zasady testów pisanych przez agenta), 6.3 (konfiguracja OpenCode).

## 1. Podział ról

| Rola | Kto | Zakres |
|---|---|---|
| Wykonawca | **model lokalny** w OpenCode (Spark przez tunel albo Ollama / llama.cpp na Macu) | wykonuje zadanie; jedyny autor zmian w kodzie ocenianego repozytorium |
| Przygotowanie i pomiar | my (człowiek + Claude Code w `spark-setup`) | zadania, klucz odpowiedzi, stan bazowy, skrypty, uruchomienie przebiegów, raporty |
| Ocena | skrypt (`check.py`) + człowiek (`review.md`) | miary obiektywne automatycznie; zgodność diagnozy i jakość zmian w przeglądzie |

Zasada: **nie rozwiązujemy zadań oceny sami** — poza kluczem odpowiedzi, który powstaje przed przebiegiem i jest ukryty przed wykonawcą. Model chmurowy (Claude) nie zmienia kodu w ocenianych repozytoriach.

## 2. Pojęcia

| Pojęcie | Znaczenie |
|---|---|
| Zadanie | katalog `bench/agent-eval/tasks/<id>/`: `task.json` (repo, stan bazowy, testy, limit czasu), `prompt.md` (polecenie, identyczne dla wszystkich modeli), `answer-key.md` (ukryty klucz), opcjonalnie `AGENTS.rules.md` |
| Stan bazowy | tag w ocenianym repo (np. `eval/t1-base`); każdy przebieg startuje z tego samego commita w osobnym `git worktree` |
| Wariant | `bare` — bez instrukcji w repo; `rules` — z `AGENTS.md` (zasady z `findings.md` 6.7); mierzy wpływ instrukcji |
| Przebieg | jedno wykonanie: model × zadanie × wariant × powtórzenie; katalog `bench/agent-eval/runs/<RRRRMMDD-HHMM>-…-r<N>/` |
| Przebieg zerowy | `check.py` na stanie bazowym, bez agenta — punkt odniesienia (ile pada, co jest niestabilne) |
| Seria | komplet przebiegów porównywanych w jednym raporcie (te same zadanie, stan bazowy, wersje) |

## 3. Procedura (środowisko developerskie)

### 3.1 Przygotowanie zadania (raz)

| Krok | Działanie |
|---|---|
| 1 | Zamrozić stan bazowy: commit w ocenianym repo (z `.gitignore` dla `node_modules/`, `test-results/`), tag `eval/<id>-base` |
| 2 | Przebieg zerowy: `python3 -I bench/agent-eval/check.py --task bench/agent-eval/tasks/<id> --repo <repo> --repeat 3 --out bench/agent-eval/runs/<data>-<id>-baseline` |
| 3 | Klucz odpowiedzi: każda pozycja z przebiegu zerowego z przyczyną, „błąd w teście / w kodzie”, właściwą poprawką i statusem; **bez pozycji „do ustalenia”** przed serią liczoną do raportu |
| 4 | Polecenie (`prompt.md`): opis problemu tak, jak napisałby go użytkownik; bez wskazówek z klucza; wymóg raportu końcowego w tabeli |

### 3.2 Przebieg

| Krok | Działanie |
|---|---|
| 1 | Model działa i ma właściwy kontekst: Spark — zestaw z `profiles/`, tunel `ssh -N spark`, `scripts/spark-health.sh`; Mac — Ollama z kontekstem ≥ 64k (B19) |
| 2 | `python3 -I bench/agent-eval/run.py --task tasks/<id> --repo <repo> --model <provider/model> --variant bare\|rules --metrics-url http://localhost:<port>/metrics --rep <N>` |
| 3 | Skrypt: worktree w `/tmp` ze stanu bazowego → `opencode run --auto --format json` z limitem czasu → `diff.patch` → `check.py` (3 powtórzenia testów) → `run.json` → wiersz w `results-<id>.csv` → szablon `review.md` |
| 4 | Przegląd człowieka: `review.md` wypełniony z kluczem obok; ocena 1–5 i liczba interwencji przepisane do CSV |
| 5 | Commit katalogu przebiegu i CSV w `spark-setup` |

Zasady przebiegu: nowa sesja OpenCode na każdy przebieg; bez interwencji (jeśli konieczna — liczyć i opisać); te same wersje (OpenCode, obraz vLLM, model z rewizji `models.yaml`) w obrębie serii; **2–3 powtórzenia** na model × wariant, bo wynik agenta jest losowy.

### 3.3 Miary

| Miara | Źródło | Uwagi |
|---|---|---|
| Testy zaliczone / wszystkie | `check.json` (ostatnie powtórzenie) | Jest i Playwright osobno |
| Pełne zaliczenie N/N | `check.json` | ile z N powtórzeń przeszło w całości — wykrywa niestabilność |
| Niestabilne testy | `check.json` | wynik różny między powtórzeniami |
| Usunięte / pominięte testy | `check.json` (`tests_removed`, `skip_or_only`) | > 0 = przebieg niezaliczony |
| Zmieniona logika | `check.json` (`logic_changed`) | dopuszczalne tylko przy pozycjach klucza „błąd w kodzie” |
| Zakres zmian | `diff.patch`, `changed_files` | pliki poza zakresem, pozostałości (`.bak`) |
| Zgodność diagnozy | `review.md` | % pozycji klucza poprawnie rozpoznanych |
| Zgodność raportu agenta z faktem | `review.md` | czy agent twierdzi „wszystko przechodzi”, gdy nie przechodzi |
| Czas, limit czasu | `run.json` | `duration_s`, `timed_out` |
| Tokeny generowane / promptu, ucięte odpowiedzi | `run.json` (`usage`, z `/metrics` vLLM) | tylko vLLM; Ollama nie publikuje metryk — wtedy z `opencode.jsonl` (do dopracowania) |
| Interwencje, ocena 1–5 | `review.md` → CSV | skala w `review-template.md` |

## 4. Środowisko analityczne (SOFA) — ta sama rama

Zadanie = zestaw pytań z oczekiwaną odpowiedzią (klucz) przygotowaną przez analityka; przebieg = model × zestaw × powtórzenie; raport jak w sekcji 6.

| Scenariusz | Wejście | Klucz | Miara obiektywna | Przegląd |
|---|---|---|---|---|
| Jakość wymagań | wymagania z modelu EA | wady wskazane przez eksperta (kategorie wg normy, np. ISO/IEC/IEEE 29148) | precyzja i czułość wykrytych wad | trafność uzasadnień |
| RAG nad EA | pytania o elementy modelu | elementy / dokumenty źródłowe | trafienie źródeł (top-k), cytowanie istniejących elementów | poprawność odpowiedzi, halucynacje |
| Text-to-SQL | pytania + schemat | zapytanie wzorcowe | zgodność **wyniku** wykonania (nie tekstu SQL) | czytelność zapytania |
| Pytania ogólne / wrażliwe | pytania tematyczne (`findings.md` 3.6) | oczekiwane zachowanie | odmowa / odpowiedź | rzetelność |

Do ustalenia z analitykami: źródło danych (anonimizacja), liczba pytań na scenariusz (min. ~20–30, żeby różnice między modelami były czytelne — szacunek), kto przygotowuje klucz.

## 5. Offline

| Wymaganie | Jak sprawdzić | Stan |
|---|---|---|
| Inferencja lokalna | model w vLLM (Spark) albo Ollama / llama.cpp (Mac); w `opencode.json` tylko dostawcy `localhost` | spełnione |
| Brak ruchu wychodzącego z narzędzi (OpenCode: lista modeli, telemetria, aktualizacje; npm, Playwright) | przebieg przy odciętej sieci zewnętrznej (np. Mac bez Wi-Fi, tunel po kablu) albo zapora z logiem połączeń | **niesprawdzone** |
| Zależności testów dostępne lokalnie | `node_modules` i przeglądarki Playwright zainstalowane przed przebiegiem; worktree dowiązuje `node_modules` z repo | spełnione dla T1 |
| Izolacja wykonawcy | `--auto` zatwierdza polecenia agenta bez pytania — przebieg w worktree w `/tmp`; docelowo osobny użytkownik albo kontener | częściowo |

## 6. Raporty

| Raport | Zawartość | Gdzie |
|---|---|---|
| Przebieg | `run.json`, `check.json`, `diff.patch`, `opencode.jsonl`, `review.md` | `bench/agent-eval/runs/<przebieg>/` |
| Zbiorczy na zadanie | wiersz na przebieg | `bench/agent-eval/results-<id>.csv` |
| Seria | tabela model × wariant: mediana zaliczonych testów, pełne zaliczenie, zgodność diagnozy, czas, tokeny, ocena; wnioski i rekomendacja | `findings.md` 3.x (nowa podsekcja z datą, `/finding`) |
| Końcowy PoC | rekomendacja modelu i sposobu pracy dla obu środowisk, ograniczenia, koszty czasu | do ustalenia (dokument dla zespołu) |

## 7. Zadania

| Id | Repo | Opis | Stan |
|---|---|---|---|
| T1 | `openMinesweeper` | naprawa padających i niestabilnych testów (Jest 5, Playwright 8 + 3 niestabilne); rozstrzygnięcie „błąd w teście czy w grze” | skrypty i polecenie gotowe; brakuje stanu bazowego (`eval/t1-base`) i kompletnego klucza |
| T2–T5 | `openMinesweeper` | nowa funkcja, wprowadzony błąd, napisanie testów, refaktor — z ukrytymi testami akceptacyjnymi (B18) | do przygotowania |

Kolejność modeli w T1: Qwen3.6-35B-A3B FP8 (Spark, zestaw C — działa), Qwen3.6 NVFP4 (Mac, Ollama), Qwen3-Coder-Next (zestaw D / Ollama 52 GB), gpt-oss-120b (zestaw A).
