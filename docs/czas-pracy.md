---
title: Czas pracy nad PoC SOFA na DGX Spark
date: 2026-10-12
language: pl
tags: [czas-pracy, rozliczenie, dgx-spark, sofa]
---

# Czas pracy

Do rozliczenia w pracy. Przy każdym wpisie podstawa, żeby było jasne, co wynika z logów i commitów, a co jest szacunkiem.

| Data | Czas | Podstawa | Pewność |
|---|---|---|---|
| 2026-10-10 | 3–5 h | dwa dokumenty koncepcyjne (`context/sofa-obserwacje.md`, `context/llm-pamiec-wzor.md` — po ~5 000 słów) i symulator `context/rag-ea-symulator.html`; jedyny znacznik czasu to `date:` we frontmatterze | **niska** — oszacowane z objętości tekstu, bez godzin. Dokładne godziny są w rozmowie na claude.ai (projekt „local ai”, `poc_output.md`) |
| 2026-10-11 | ~10 h (14:00 → ~24:00) | raport audytu `audyt-spark-spark-28e3-20261011-1400.txt`, 21 commitów między 16:44 i 23:57, znaczniki startów modeli i benchmarków w `findings.md` 3.1, 3.4–3.7 | **wysoka** co do rozpiętości. W tym ~3 h 20 min czekania na pobierania (17:24–17:57), starty vLLM (zestaw B 10–15 min, gpt-oss ~8 min, Gemma 3 min, dwa przełączenia zestawów) i trzy benchmarki — praca nadzorowana, nie bezczynność |
| **Razem** | **13–15 h** | | |

Zakres prac obu dni: audyt maszyny przy przejęciu, konto i bootstrap hosta, pobranie modeli, uruchomienie zestawów B i A, diagnoza dwóch znalezisk blokujących start (`findings.md` 3.2, 3.3), pomiary pamięci i wydajności czterech modeli, Open WebUI, test tematyczny, złożenie repozytorium i dokumentacji (findings, decisions, backlog).

## Jak dopisywać

- Jeden wiersz na dzień, data w formacie RRRR-MM-DD, najnowszy na końcu.
- W kolumnie „Podstawa” konkretne ślady: nazwy plików, godziny commitów, znaczniki w logach. Bez tego wpis jest nie do obrony.
- „Pewność” wysoka tylko wtedy, gdy rozpiętość wynika z commitów, logów albo nazw plików; szacunki z objętości pracy oznaczać jako niską.
- Czekanie na pobierania i starty modeli liczy się jako praca nadzorowana, ale wydzielać je w kolumnie „Podstawa”, żeby było widoczne.
