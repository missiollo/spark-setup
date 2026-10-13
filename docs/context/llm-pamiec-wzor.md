---
title: Szacowanie maksymalnego rozmiaru modelu LLM na podstawie RAM
date: 2026-10-10
language: pl
tags: [llm, ram, kwantyzacja, macos, apple-silicon, dgx-spark, kv-cache, modele]
---

# Szacowanie maksymalnego rozmiaru modelu LLM na podstawie RAM

## 1. Wzór

```
parametry_mld = (RAM_GB × (1 − rezerwa)) / bajty_na_parametr
```

| Symbol | Znaczenie | Jednostka | Wartość domyślna |
|---|---|---|---|
| `RAM_GB` | Całkowita pamięć (zunifikowana) | GB | — |
| `rezerwa` | Część RAM dla systemu, KV cache, runtime'u | ułamek | 0.25 (macOS) |
| `bajty_na_parametr` | Pamięć na jeden parametr modelu | B | 0.6 (Q4_K_M) |
| `parametry_mld` | Maksymalna liczba parametrów modelu | mld (B) | — |

Postać uproszczona dla wartości domyślnych: `parametry_mld ≈ 1.25 × RAM_GB`.

## 2. Założenia

### 2.1 Rezerwa pamięci

| Składnik rezerwy | Opis |
|---|---|
| System operacyjny i aplikacje | Pamięć poza modelem |
| KV cache | Pamięć kontekstu; rośnie liniowo z długością promptu |
| Bufory runtime'u | llama.cpp, MLX, Ollama, vLLM itp. |

| Platforma | Typowa rezerwa | Źródło |
|---|---|---|
| macOS, RAM > 36 GB | 25% | Domyślny limit GPU = 75% pamięci zunifikowanej |
| macOS, RAM ≤ 36 GB | ~33% | Domyślny limit GPU ≈ 2/3 pamięci |
| Linux, DGX Spark | ~10–15 GB (≈ 10–12%) | Brak sztywnego limitu GPU; CUDA używa prawie całej pamięci |

Uwaga: limit GPU na macOS można podnieść: `sudo sysctl iogpu.wired_limit_mb=<MB>`.

### 2.2 Bajty na parametr (precyzja / kwantyzacja)

| Format | Bitów/param | Bajty/param | Uwagi |
|---|---|---|---|
| FP16 / BF16 | 16 | 2.0 | Pełna precyzja inferencji |
| FP8 | 8 | 1.0 | Sprzętowo na Hopper/Blackwell |
| Q8_0 (GGUF) | ~8.5 | ~1.06 | Praktycznie bez straty jakości |
| Q4_K_M (GGUF) | ~4.8 | ~0.6 | Domyślne założenie wzoru |
| NVFP4 / MXFP4 | ~4.25–4.5 | ~0.5–0.56 | Sprzętowo na Blackwell (DGX Spark) |
| Q3_K_M | ~3.9 | ~0.45 | Zauważalna utrata jakości |
| Q2_K | ~2.6–3 | ~0.35 | Duża utrata jakości |

## 3. Wyniki: macOS (rezerwa 25%, Q4 = 0.6 B/param)

| RAM [GB] | Dostępne na model [GB] | Maks. model [mld param] |
|---|---|---|
| 36 | 27 | ~45 (realnie ~40, limit 2/3) |
| 48 | 36 | 60 |
| 64 | 48 | 80 |
| 96 | 72 | 120 |
| 128 | 96 | 160 |

## 4. Wyniki: DGX Spark 128 GB (~112 GB dostępne)

| Format | Bajty/param | Maks. model [mld param] |
|---|---|---|
| FP16 / BF16 | 2.0 | ~55 |
| FP8 / Q8 | ~1.0 | ~110 |
| Q4_K_M | ~0.6 | ~185 |
| NVFP4 / MXFP4 | ~0.5–0.55 | ~200 |

| Konfiguracja | Maks. model (deklaracja NVIDII) |
|---|---|
| 1 × DGX Spark | ~200 mld (FP4) |
| 2 × DGX Spark (ConnectX) | ~405 mld (FP4) |

## 5. Pojemność a prędkość

Prędkość generowania (decode) jest ograniczona przepustowością pamięci:

```
tokeny_na_s_max ≈ przepustowość_GB_s / rozmiar_aktywnych_wag_GB
```

Realna prędkość to zwykle ok. 50–70% wyliczonego sufitu.

Kolumny przykładowe:
- `dense_70B_Q4`: model gęsty 70B w Q4, ~40 GB czytane na każdy token.
- `moe_gpt-oss-120b`: model MoE, ~5.1 mld aktywnych parametrów w MXFP4, ~3 GB czytane na token; wymaga ~63 GB na wagi.

| Platforma | Wariant | Maks. RAM [GB] | Przepustowość [GB/s] | dense_70B_Q4: sufit tok/s | moe_gpt-oss-120b: sufit tok/s |
|---|---|---|---|---|---|
| M5 | — | 32 | 153 | nie mieści się | nie mieści się |
| M5 Pro | 16/20-core GPU | 64 | 307 | ~7.7 | nie mieści się (limit 75% = 48 GB) |
| M5 Max | 32-core GPU | 36 | 460 | nie mieści się | nie mieści się |
| M5 Max | 40-core GPU | 128 | 614 | ~15 | ~200 |
| M4 Pro | — | 64 | 273 | ~6.8 | nie mieści się |
| M4 Max | 32-core GPU | 36 | 410 | nie mieści się | nie mieści się |
| M4 Max | 40-core GPU | 128 | 546 | ~13.7 | ~180 |
| M3 Max | 30-core GPU | 96 | 300 | ~7.5 | ~100 |
| M3 Max | 40-core GPU | 128 | 400 | ~10 | ~130 |
| DGX Spark | GB10 | 128 | 273 | ~6.8 | ~90 |

Wnioski:
- M5 Max z 40-core GPU (614 GB/s, do 128 GB) to obecnie najszybsza opcja w tym zestawieniu do lokalnych LLM.
- M5 Max z 32-core GPU jest dostępny tylko z 36 GB RAM, więc mimo 460 GB/s nie uruchomi dużych modeli.
- M5 Pro (do 64 GB, 307 GB/s) jest dobry dla modeli do ~30–40 mld lub MoE do ~80 mld w Q4.
- DGX Spark ma pojemność M5 Max 128 GB, ale ok. 2,2× mniejszą przepustowość. Nadrabia mocnym prefillem (przetwarzanie promptu), CUDA i formatem FP4.
- Na platformach z niższą przepustowością modele MoE dają wielokrotnie szybsze generowanie niż modele gęste o podobnej jakości.

## 6. Przykładowe modele i zastosowania

Rozmiary wag liczone dla Q4 (~0.6 B/param) albo natywnego formatu modelu. Do wag trzeba doliczyć KV cache (sekcja 7).

### 6.1 Modele językowe

| Model | Architektura | Parametry (aktywne) | Wagi Q4 [GB] | Min. platforma | Zastosowanie | Uzasadnienie |
|---|---|---|---|---|---|---|
| Gemma 4 E4B | dense (edge) | ~4 mld | ~3–5 | M5 / dowolny Mac 16 GB | Szybkie zadania pomocnicze, klasyfikacja, routing w agentach | Bardzo mały i szybki; dobry jako tani model "pierwszej linii" |
| Gemma 4 12B | dense | 12 mld | ~7.5 | M5 24 GB | Asystent ogólny, multimodalność (obraz, audio) | Dobra jakość przy małej pamięci; natywne wejście obrazu i audio |
| gpt-oss-20b | MoE | 21 mld (3.6 mld) | ~13 (MXFP4) | M5 24–32 GB | Rozumowanie, tool calling, lokalny agent | Mocne rozumowanie przy ~16 GB; Apache 2.0; dobre wsparcie narzędzi |
| Gemma 4 26B-A4B | MoE | 26 mld (~4 mld) | ~16 | M5 Pro 48 GB | Asystent ogólny, szybki czat, długie sesje | MoE = szybkie generowanie; jeden z najpopularniejszych modeli lokalnych 2026 |
| Gemma 4 31B | dense | 31 mld | ~19 | M5 Pro 48 GB | Wyższa jakość tekstu, streszczenia, analiza dokumentów | Gęsty, więc wolniejszy od MoE, ale stabilniejsza jakość; dobrze działa na MLX |
| Qwen3.6-27B | dense | 27 mld | ~16 | M4/M5 Pro 48 GB | Kodowanie, praca z repozytorium, stabilne odpowiedzi | Gęsty model nastawiony na stabilność i kodowanie; kontekst 262k; multimodalny |
| Qwen3.6-35B-A3B | MoE | 35 mld (3 mld) | ~21 | M4/M5 Pro 48 GB | Agenci, tool calling, szybki asystent ogólny, wielojęzyczność | Hybrydowa uwaga (Gated DeltaNet) = tani długi kontekst; tekst, obraz, wideo; Apache 2.0 |
| Qwen3.8-27B | dense | 27 mld | ~16 | M4/M5 Pro 48 GB | Najwyższa jakość w klasie ~30B: kod, analiza, rozumowanie | Nowsza generacja niż 3.6 przy tej samej pamięci; multimodalny; licencja do sprawdzenia |
| Qwen3.8-Flash-Next | MoE (+ n-gram embedding) | 125 mld + 51 mld embedding (6 mld) | ~105 (Q4), ~80 (Q3) | DGX Spark (Q3/Q4 na styk) | Agenci, kod, bardzo długi kontekst (do 1M) | Podgląd architektury Qwen4; tylko 6 mld aktywnych = szybki; ale ~176 mld na dysku, na 128 GB tylko w niskiej kwantyzacji |
| Qwen3.8 (2.4T-A95B) | MoE | 2400 mld (95 mld) | >1000 | klaster GPU | — (nie do użytku lokalnego) | Klasa Qwen-Max; wymienione dla kompletności |
| Qwen3-Coder-Next | MoE | 80 mld (3 mld) | ~48 | M5 Pro 64 GB* / M5 Max 64 GB | Agenci programistyczni, refaktoryzacja, kod w IDE/CLI | Wyspecjalizowany do agentowego kodowania i tool callingu; kontekst 256k; prędkość jak model 3B |
| gpt-oss-120b | MoE | 117 mld (5.1 mld) | ~63 (MXFP4) | M5 Max 128 GB / DGX Spark | Rozumowanie, RAG, agent z narzędziami, ogólny "ChatGPT lokalnie" | Najlepszy stosunek jakości do pamięci w klasie ~120B; natywny MXFP4 pasuje do Blackwella |
| Qwen3.5-122B (MoE) | MoE | ~122 mld (~10 mld) | ~73 | M5 Max 128 GB / DGX Spark | Najwyższa jakość ogólna w zasięgu 128 GB, analiza złożonych dokumentów | Większy i mocniejszy od gpt-oss-120b, ale więcej aktywnych parametrów, więc wolniejszy |

\* Na M5 Pro 64 GB wymaga podniesienia `iogpu.wired_limit_mb` (domyślny limit 48 GB jest na styk bez KV cache).

### 6.2 Modele embeddingowe (do RAG)

| Model | Rozmiar | Wagi [GB] | Zastosowanie | Uzasadnienie |
|---|---|---|---|---|
| bge-m3 | ~0.6 mld | ~1–2 | Wyszukiwanie semantyczne, wielojęzyczne dokumenty | Wielojęzyczny, wspiera dense + sparse retrieval; lekki |
| Qwen3-Embedding (0.6B / 4B / 8B) | 0.6–8 mld | ~1–16 | Embeddingi wysokiej jakości do RAG | Skalowalny rozmiar; czołowe wyniki w benchmarkach retrievalu |

### 6.3 Dobór według platformy

| Platforma | Rekomendowany zestaw | Uwagi |
|---|---|---|
| M5 / Mac 24–32 GB | gpt-oss-20b lub Gemma 4 12B + bge-m3 | Kontekst trzymać umiarkowany |
| M4 Pro 48 GB | Qwen3.6-35B-A3B (szybki) + Qwen3.8-27B (jakość) + bge-m3 | Szczegóły w 6.4 |
| M5 Pro 48–64 GB | Qwen3.6-35B-A3B, Qwen3.8-27B, Gemma 4 26B-A4B; Qwen3-Coder-Next do kodu (64 GB) | Modele MoE dają dobrą prędkość przy 307 GB/s |
| M5 Max 128 GB (40-core) | gpt-oss-120b lub Qwen3.5-122B + Qwen3-Embedding-8B | Najszybsza opcja; miejsce na długi kontekst przy gpt-oss-120b |
| DGX Spark 128 GB | gpt-oss-120b (MXFP4) + Qwen3-Embedding; Qwen3-Coder-Next do kodu; Qwen3.8-Flash-Next do testów (niska kwantyzacja) | Preferować MoE i formaty FP4; mocny prefill pomaga przy RAG |

### 6.4 Konfiguracja: MacBook Pro M4 Pro, 48 GB RAM (komputer służbowy)

Parametry:

| Parametr | Wartość |
|---|---|
| RAM | 48 GB |
| Przepustowość pamięci | 273 GB/s |
| Domyślny limit GPU (75%) | 36 GB |
| Maks. model wg wzoru (Q4) | 36 / 0.6 = 60 mld (bez zapasu na kontekst) |
| Praktyczny cel (z KV cache 8–15 GB) | modele do ~35 mld w Q4 lub ~27 mld w Q6 |

Modele:

| Model | Kwantyzacja | Wagi [GB] | Zapas na KV cache [GB] | Sufit tok/s | Ocena | Zastosowanie |
|---|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | Q4_K_M | ~21 | ~15 | ~150 (realnie ~60–90) | Najlepszy domyślny wybór | Codzienny asystent, agenci, tool calling, długi kontekst |
| Qwen3.8-27B | Q4_K_M | ~16 | ~20 | ~17 (realnie ~10–12) | Najlepsza jakość | Trudniejsze zadania: kod, analiza, rozumowanie |
| Qwen3.8-27B | Q6_K | ~22 | ~14 | ~12 (realnie ~7–9) | Wyższa jakość, wolniej | Gdy jakość ważniejsza niż prędkość |
| Qwen3.6-27B | Q4_K_M | ~16 | ~20 | ~17 (realnie ~10–12) | Alternatywa dla 3.8-27B | Kodowanie, gdy licencja Apache 2.0 jest wymagana |
| Gemma 4 26B-A4B | Q4_K_M | ~16 | ~20 | ~115 (realnie ~50–70) | Dobra alternatywa MoE | Asystent ogólny, multimodalność |
| gpt-oss-20b | MXFP4 | ~13 | ~23 | ~135 (realnie ~60–80) | Lekki, szybki | Rozumowanie, lokalny agent, równolegle z innym modelem |
| bge-m3 / Qwen3-Embedding-4B | — | ~1–8 | — | — | Do RAG | Embeddingi dokumentów |
| Qwen3-Coder-Next | Q4_K_M | ~48 | brak | — | Nie mieści się | Wymaga 64 GB+ |
| gpt-oss-120b | MXFP4 | ~63 | brak | — | Nie mieści się | Wymaga 96–128 GB |
| Qwen3.8-Flash-Next | Q3+ | ~80+ | brak | — | Nie mieści się | Wymaga DGX Spark lub większej maszyny |

Rekomendacja:
- Domyślnie: Qwen3.6-35B-A3B, który jest szybki, ma długi kontekst i zostawia dużo pamięci.
- Do trudniejszych zadań: Qwen3.8-27B (Q4 albo Q6). Jest gęsty, więc ok. 6–8× wolniejszy od MoE.
- Para "model + embedding" (np. Qwen3.6-35B-A3B + bge-m3) mieści się razem z zapasem na kontekst, co wystarcza do lokalnego RAG.
- Limit GPU można podnieść do ~40–42 GB (`sudo sysctl iogpu.wired_limit_mb=40960`), jeśli inne aplikacje nie potrzebują dużo pamięci. Na komputerze służbowym warto sprawdzić, czy polityki IT na to pozwalają.
- Przy przepustowości 273 GB/s M4 Pro generuje mniej więcej tak szybko jak DGX Spark; różnica jest w pojemności (48 vs 128 GB).

## 7. Ograniczenia wzoru

| Czynnik | Wpływ | Zalecenie |
|---|---|---|
| Długi kontekst (32k–128k) | KV cache: kilka do kilkunastu+ GB | Zwiększyć rezerwę o 15–30 GB |
| Modele MoE | W pamięci muszą być WSZYSTKIE parametry | Liczyć sumę parametrów, nie aktywne |
| RAG | Długie prompty = duży KV cache | Celować w 70–120 mld (najlepiej MoE) zamiast maksimum |
| Małe Maki (≤ 36 GB) | Domyślny limit GPU ~2/3 RAM | Rezerwa 33% lub podnieść `iogpu.wired_limit_mb` |
| "Mieści się" ≠ "jest szybki" | Prędkość zależy od przepustowości | Patrz sekcja 5 |
| Szybko zmieniający się rynek modeli | Lista z sekcji 6 dezaktualizuje się w ciągu miesięcy | Weryfikować aktualne wersje przed wdrożeniem |

## 8. Podsumowanie

- Wzór szacuje górną granicę rozmiaru modelu w kwantyzacji ~4-bitowej przy umiarkowanym kontekście.
- 25% rezerwy odpowiada domyślnemu limitowi GPU w macOS (75% pamięci zunifikowanej).
- 0.6 B/param odpowiada kwantyzacji Q4_K_M (~4.8 bita).
- Na DGX Sparku rezerwa jest mniejsza (~10–15 GB), a FP4 daje ~200 mld parametrów, ale przepustowość (~273 GB/s) faworyzuje modele MoE.
- M5 Max 40-core (614 GB/s, 128 GB) jest najszybszą platformą w zestawieniu; M5 Pro (307 GB/s, 64 GB) wystarcza dla modeli MoE do ~80 mld.
- Najbardziej uniwersalny wybór dla 128 GB to gpt-oss-120b; do kodu Qwen3-Coder-Next.
- Na M4 Pro 48 GB najlepiej sprawdzają się Qwen3.6-35B-A3B (prędkość) i Qwen3.8-27B (jakość).
- Większe modele Qwen3.8 (Flash-Next, 2.4T) nie mieszczą się na laptopie; Flash-Next ma sens dopiero na DGX Sparku w niskiej kwantyzacji.

## 9. Alternatywa: AMD Ryzen AI Max+ (Strix Halo) vs DGX Spark

| Cecha | AMD Ryzen AI Max+ (Strix Halo) | DGX Spark |
|---|---|---|
| Pamięć | 128 GB zunifikowanej | 128 GB zunifikowanej |
| Przepustowość | ~256 GB/s | ~273 GB/s |
| Decode (tok/s) | praktycznie jak Spark | praktycznie jak Strix Halo |
| Prefill (moc obliczeniowa) | słabszy (RDNA 3.5, brak sprzętowego FP4) | znacznie mocniejszy (Blackwell, FP8/FP4) |
| Stos oprogramowania | ROCm, Vulkan (llama.cpp); mniej dojrzały | CUDA, vLLM, TensorRT-LLM; dojrzały |
| Serwowanie wielu użytkowników | ograniczone | dojrzałe (vLLM, batching) |
| Zakup / wsparcie w instytucji | często mini-PC mniej znanych producentów (wyjątek: HP Z2 Mini G1a) | wsparcie enterprise NVIDIA |
| Cena | zwykle wyraźnie niższa | wyższa |

Uwagi do materiałów marketingowych:
- "Qwen3 235B MoE" na 128 GB: 235 × 0.6 ≈ 141 GB w Q4, więc nie mieści się; tylko Q2/Q3 ze stratą jakości.
- "Giant-context document analysis": pojemnościowo możliwe, ale wolne przez słaby prefill.
- "Kilka modeli naraz" (LLM + embedding + reranker): realne, ale tak samo na Sparku.

Wnioski dla wniosku o PoC (RAG nad modelami Enterprise Architect):
- Uwzględnić Strix Halo jako rozważaną alternatywę.
- Główny argument za Sparkiem: RAG = długie prompty = potrzeba mocnego prefillu.
- Prototyp można zrobić na M4 Pro 48 GB (podobna przepustowość), a Spark uzasadnić większymi modelami i obsługą wielu użytkowników.

## 10. Prefill, TTFT i decode

### 10.1 Fazy odpowiedzi modelu

| Faza | Co się dzieje | Wąskie gardło | Metryka |
|---|---|---|---|
| Prefill | Przetworzenie całego promptu naraz (duże mnożenia macierzy), budowa KV cache | Moc obliczeniowa (TFLOPS) | TTFT (time to first token) |
| Decode | Generowanie tokenów jeden po drugim; każdy token czyta wszystkie aktywne wagi | Przepustowość pamięci (GB/s) | tokeny/s |

### 10.2 Wzory

```
FLOP_prefill ≈ 2 × aktywne_parametry × tokeny_promptu  (+ koszt attention)
czas_prefill ≈ FLOP_prefill / efektywne_TFLOPS
czas_całkowity ≈ TTFT + tokeny_odpowiedzi / tokeny_na_s
```

### 10.3 Czynniki wpływające na prefill

| Czynnik | Wpływ |
|---|---|
| Moc obliczeniowa GPU (TFLOPS, tensor cores) | Główny czynnik; Spark > Strix Halo, Maki |
| Sprzętowa niska precyzja (FP8, FP4) | Każde zejście o połowę precyzji ≈ 2× więcej operacji/s (jeśli sprzęt wspiera) |
| Aktywne parametry | MoE tańsze: gpt-oss-120b (5.1 mld aktywnych) ≈ 14× taniej niż dense 70B |
| Długość promptu | Liniowo (MLP), kwadratowo (attention); przy 32k+ attention dominuje |
| Architektura attention | Liniowa/hybrydowa (np. Gated DeltaNet w Qwen3.6) tnie koszt długiego kontekstu |
| Oprogramowanie | Flash Attention, dopracowane kernele (CUDA/TensorRT-LLM), chunked prefill |
| Prefix / prompt caching | Stały początek promptu liczony raz, potem z cache |

### 10.4 Rząd wielkości: prompt 10 000 tokenów

| Model | FLOP prefill | Charakter |
|---|---|---|
| gpt-oss-120b (5.1 mld aktywnych) | ~100 TFLOP | Spark: kilka sekund lub mniej; Strix Halo / M4 Pro: kilka razy dłużej |
| Dense 70B | ~1.4 PFLOP | Spark: kilkanaście sekund; słabsze GPU: minuta lub więcej |

Wartości orientacyjne; realne czasy zależą od runtime'u.

### 10.5 Praktyka dla RAG nad modelami EA

| Technika | Efekt |
|---|---|
| Modele MoE | Szybki prefill i szybki decode |
| Stały system prompt na początku, zmienne fragmenty na końcu | Prefix caching (vLLM, llama.cpp) pomija ponowne liczenie |
| Reranker przed LLM | Mniej, trafniejszych fragmentów = krótszy prompt = niższy TTFT |
| Mierzenie TTFT osobno od tok/s | Dla analityka czekającego na odpowiedź TTFT przy długim kontekście bywa ważniejsze |

### 10.6 Symulator (plik `rag-ea-symulator.html`)

Interaktywne porównanie dwóch platform dla tego samego modelu i długości kontekstu. Przykładowe pytanie: "Które wymagania w pakiecie »Kontrola graniczna« nie mają przypisanego komponentu realizującego?"

Aktualizacja 2026-10-13: dla DGX Spark symulator używa pomiarów z `make bench` (TTFT bez prefix cache i decode interpolowane po długości promptu, wagi zmierzone; `findings.md` 3.4–3.5) i zawiera Gemmę 4 26B-A4B. Tabele poniżej to założenia pierwotne; dla Sparka nieaktualne (np. efektywne TFLOPS ~30–130 zależnie od modelu zamiast ~80, pamięć 121,69 GiB).

Założenia platform (efektywne TFLOPS to szacunki do podmiany na pomiary):

| Platforma | Efektywne TFLOPS (prefill) | Przepustowość [GB/s] | Pamięć dla modelu [GB] |
|---|---|---|---|
| DGX Spark | ~80 | 273 | ~112 |
| M3 Max 128 GB (40-core GPU) | ~14 | 400 | 96 |
| M4 Pro 48 GB | ~8 | 273 | 36 |
| Strix Halo | ~20 | 256 | ~110 |

Założenia modeli:

| Model | Aktywne param. [mld] | Aktywne wagi na token [GB] | Wagi łącznie [GB] |
|---|---|---|---|
| Qwen3.6-35B-A3B (MoE) | 3 | ~1.8 | ~21 |
| Qwen3.8-27B (dense) | 27 | ~16 | ~16 |
| gpt-oss-120b (MoE) | 5.1 | ~3 | ~63 |

Pozostałe założenia: wyszukiwanie 0.4 s, decode ≈ 60% teoretycznej przepustowości, KV cache ≈ 0.15 GB na 1k tokenów, odpowiedź 400 tokenów.

Obserwacje:
- M3 Max ma najszybszy decode (400 GB/s), ale prefill kilka razy wolniejszy niż Spark.
- Spark wygrywa TTFT przy długim kontekście RAG; przy krótkich promptach przewaga maleje.
- Zamiana dense → MoE skraca jednocześnie prefill i decode.

### 10.7 Jak budować prompt, żeby prefill był jak najkrótszy

Dwie dźwignie: mniej tokenów do przeliczenia i ponowne użycie już przeliczonych (prefix caching).

#### Kolejność sekcji promptu (od najbardziej stałych do najbardziej zmiennych)

| Kolejność | Sekcja | Zmienność | Cache |
|---|---|---|---|
| 1 | System prompt: rola, zasady oceny jakości wymagań | stała | zawsze trafiony |
| 2 | Definicje narzędzi (tool calling) | stała | zawsze trafiony |
| 3 | Opis schematu EA i słownik (typy elementów, relacji, konwencje ID) | stała | zawsze trafiony |
| 4 | Przykłady few-shot (jeśli są) | stała | zawsze trafiony |
| 5 | Kontekst pakietu / projektu (półstały) | rzadko się zmienia | trafiony w ramach sesji |
| 6 | Fragmenty z wyszukiwania (posortowane deterministycznie, np. po ID) | per pytanie | częściowo |
| 7 | Historia rozmowy (skrócona) | rośnie | częściowo |
| 8 | Pytanie użytkownika | zawsze nowa | nie |

Zasada: cokolwiek zmienne (data, nazwa użytkownika, ID sesji) nigdy na początku promptu — jedna zmieniona linia na górze unieważnia cache dla całej reszty.

#### Mniej tokenów

| Technika | Przykład | Efekt |
|---|---|---|
| Zwarty format elementów EA zamiast XMI/JSON | `REQ-112 \| Weryfikacja dokumentu \| pakiet: Kontrola graniczna \| realizuje: –` | często 3–5× mniej tokenów niż XML/JSON |
| Usunięcie GUID-ów i metadanych technicznych | krótkie ID zamiast `{3F2504E0-4F89-...}` | GUID to ~20–30 tokenów każdy |
| Chunking po elemencie modelu | 1 element (z relacjami 1. stopnia) = 1 fragment | brak "doklejonych" nieistotnych treści |
| Mniejsze top-k + reranker | wyszukaj 30, po rerankingu przekaż 5–8 | krótszy prompt i lepsza trafność |
| Deduplikacja fragmentów | ten sam element z kilku ścieżek tylko raz | mniej powtórzeń |
| Instrukcje po angielsku | treść modeli w oryginale, instrukcje po angielsku | polski tokenizuje się zwykle drożej |
| Skracanie historii | streszczenie starszych tur; usuwanie starych fragmentów RAG | kontekst nie rośnie bez końca |

#### Zapytania strukturalne zamiast RAG

Pytania o strukturę modelu (brakujące relacje, liczności, pokrycie wymagań) lepiej obsłużyć narzędziem, które odpytuje repozytorium EA (baza danych z tabelami obiektów i powiązań), a do modelu przekazać tylko wynik. Przykład: "wymagania bez komponentu realizującego" to zapytanie po relacjach, a nie wyszukiwanie semantyczne. Prompt ma wtedy kilkaset tokenów zamiast kilkunastu tysięcy. RAG zostaje dla pytań o treść (opisy, notatki, jakość sformułowań).

#### Ustawienia serwera

| Runtime | Ustawienie | Efekt |
|---|---|---|
| vLLM | automatic prefix caching (włączony domyślnie w nowszych wersjach) | ponowne użycie KV cache dla wspólnych prefiksów |
| vLLM | chunked prefill | długi prefill nie blokuje innych użytkowników |
| llama.cpp | `--cache-reuse`, sloty z zachowanym cache | ponowne użycie prefiksu w sesji |
| MLX / LM Studio | prompt cache w sesji | szybsze kolejne tury rozmowy |

#### Szablon promptu (szkic)

```
[SYSTEM — stały]
You are an assistant for requirements quality analysis over Enterprise Architect models.
Rules: ... Output format: ...

[TOOLS — stałe]
query_ea_repository(sql), search_ea_elements(text, top_k)

[SCHEMA — stały]
Element types: Requirement (REQ-*), Component (CMP-*), ...
Relations: realizes, traces, depends ...

[PACKAGE CONTEXT — półstały]
Package: Kontrola graniczna; scope: ...

[RETRIEVED — zmienny, sortowany po ID]
REQ-112 | Weryfikacja dokumentu | realizuje: –
REQ-118 | Zapis zdarzenia | realizuje: –

[QUESTION — zmienne]
Które wymagania w pakiecie „Kontrola graniczna” nie mają przypisanego komponentu realizującego?
```

### 10.8 Embedding, prefill i decode — rozróżnienie

| Krok | Co się dzieje | Wąskie gardło | Szybsza platforma |
|---|---|---|---|
| Embedding (tylko RAG) | osobny, mały model zamienia pytanie na wektor do wyszukiwania fragmentów | pomijalne (ułamek sekundy) | bez znaczenia |
| Prefill | duży model przetwarza cały prompt naraz, buduje KV cache | moc obliczeniowa (TFLOPS) | DGX Spark |
| Decode | duży model generuje odpowiedź token po tokenie; każdy token czyta wszystkie aktywne wagi | przepustowość pamięci (GB/s) | M3 Max (400 GB/s vs 273 GB/s) |

Analogia: prefill = przeczytanie i zrozumienie tekstu (liczy się szybkość myślenia); decode = pisanie słowo po słowie z kartkowaniem całego słownika przed każdym słowem (liczy się szybkość kartkowania).

| Profil zapytania | Dominuje | Wygrywa |
|---|---|---|
| Długi prompt, krótka odpowiedź (RAG 16k) | prefill | Spark |
| Krótki prompt, długa odpowiedź (text-to-SQL, czat, reasoning) | decode | Mac (M3 Max) |

### 10.9 KV cache (Key–Value cache)

W mechanizmie uwagi każdy token tworzy wektory Query (czego szukam), Key (po czym mnie znaleźć) i Value (jaką treść przekazuję). Nowy token porównuje swoje Q z K wszystkich poprzednich tokenów i zbiera ich V. KV cache przechowuje K i V poprzednich tokenów, żeby nie liczyć ich ponownie.

| Faza | Operacja na KV cache |
|---|---|
| Prefill | K i V liczone dla wszystkich tokenów promptu naraz i zapisywane |
| Decode | każdy nowy token liczy tylko własne K i V i dopisuje je na koniec; zapisane wartości są tylko odczytywane |

W obrębie jednej odpowiedzi KV cache jest wyłącznie dopisywany, nigdy przeliczany od początku.

Rozmiar:

```
KV_cache ≈ 2 × warstwy × głowice_KV × wymiar_głowicy × bajty × tokeny
```

Przykład (model ~30B: 64 warstwy, 8 głowic KV, wymiar 128, FP16): ~0.25 MB/token → ~0.25 GB na 1k tokenów → ~8 GB na 32k tokenów. Modele z uwagą hybrydową/liniową (np. Qwen3.6, Gated DeltaNet) mają znacznie mniejszy KV cache przy długim kontekście.

Kiedy KV cache jest jednak przeliczany:

| Sytuacja | Skutek |
|---|---|
| Kolejna tura, prompt różni się od poprzedniego (np. usunięte rozumowanie) | przeliczenie od miejsca różnicy; początek z prefix cache, jeśli włączony |
| Runtime bez prefix caching | każde wywołanie = prefill całej historii od zera |
| Brak pamięci przy wielu użytkownikach (vLLM) | wywłaszczenie zapytania, po wznowieniu przeliczenie |
| Przekroczenie okna kontekstu | przycięcie / przesunięcie kontekstu i częściowa przebudowa |

### 10.10 Reasoning (tryb thinking)

Reasoning to dodatkowe tokeny generowane w fazie decode przed właściwą odpowiedzią:

```
prefill (prompt) → decode: tokeny myślenia → decode: tokeny odpowiedzi
```

| Aspekt | Wpływ reasoningu |
|---|---|
| Prefill | bez zmian |
| Decode | wydłużony o tokeny myślenia (często 500–3000) |
| KV cache | rośnie o tokeny myślenia (dopisywanie, bez przeliczania) |
| TTFT | mylący: pierwszy token to token myślenia; mierzyć też czas do pierwszego tokena odpowiedzi |
| Prefix caching | nie pomaga (rozumowanie generowane od nowa przy każdym pytaniu) |
| Wielu użytkowników | dłuższy KV cache per zapytanie = mniej zapytań równolegle w pamięci |
| Wybór platformy | wąskie gardło przesuwa się w stronę przepustowości: rośnie przewaga M3 Max i modeli MoE |

Czas samego rozumowania (1000 tokenów, szacunki):

| Model i platforma | Czas |
|---|---|
| gpt-oss-120b, DGX Spark (~55 tok/s) | ~18 s |
| gpt-oss-120b, M3 Max (~80 tok/s) | ~13 s |
| Qwen3.8-27B, DGX Spark / M4 Pro (~10 tok/s) | ~100 s |
| Qwen3.8-27B, M3 Max (~15 tok/s) | ~65 s |

Sterowanie: gpt-oss — poziomy wysiłku (low / medium / high); Qwen — przełącznik trybu thinking.

| Zadanie | Poziom rozumowania |
|---|---|
| Routing, wybór narzędzia | niski / wyłączony |
| Interpretacja wyniku zapytania | niski |
| Text-to-SQL | średni |
| Ocena jakości wymagań (wsadowo) | średni (do przetestowania) |
| Pytania o strukturę modelu | nie zastępuje SQL — rozumowanie nie daje kompletności danych |

### 10.11 Prefix caching

Ponowne użycie KV cache dla identycznego początku promptu. Serwer dzieli prompt na bloki, identyfikuje je skrótem (hash) sekwencji od początku i trzyma policzone bloki w pamięci; nowe zapytanie ze wspólnym prefiksem liczy tylko nową końcówkę.

Zasada: dopasowanie od pierwszego tokena, co do tokena. Pierwsza różnica unieważnia cache dla całej reszty.

| Prompt | Efekt |
|---|---|
| `[system][narzędzia][schemat]` + pytanie | prefiks trafiony, liczone tylko pytanie |
| `[data][system][narzędzia][schemat]` + pytanie | zmienna data na początku = cache chybiony dla całości |
| stałe sekcje + fragmenty RAG w losowej kolejności | stała część trafiona, fragmenty liczone od nowa |

Zysk (stały prefiks ~4000 tokenów, pytanie ~100 tokenów, Qwen3.8-27B):

| Platforma | Prefill bez cache | Z cache |
|---|---|---|
| DGX Spark | ~3 s | <0.1 s |
| M3 Max | ~15 s | ~0.4 s |
| M4 Pro | ~25–30 s | ~0.7 s |

| Zastosowanie | Zysk |
|---|---|
| Kolejne pytania z tym samym system promptem | stały prefiks liczony raz |
| Kolejne tury rozmowy | historia z cache, liczona tylko nowa tura |
| Wielu analityków na Sparku | wspólny system prompt i opis schematu liczone raz dla wszystkich |
| Ocena wsadowa wymagań | ta sama instrukcja i kryteria dla każdej porcji |

Ograniczenia: zajmuje pamięć (bloki usuwane wg LRU), pomaga tylko w prefillu (nie w decode i reasoningu), wymaga identycznych tokenów (spacja, kolejność narzędzi, szablon czatu).

Odpowiednik w chmurowych API: prompt caching (Anthropic, OpenAI), zwykle z niższą ceną za tokeny z cache.

### 10.12 Usuwanie rozumowania z historii rozmowy

Cel: tokeny myślenia z poprzednich tur nie trafiają z powrotem do promptu, więc kontekst kolejnych tur nie rośnie o tysiące tokenów, a prefill pozostaje krótki.

Mechanizm: nie usuwa się KV cache ręcznie, tylko buduje się historię bez rozumowania. Serwer sam wykryje różnicę promptu i przeliczy końcówkę od miejsca zmiany; wspólny początek zostanie wzięty z prefix cache.

| Element | Jak |
|---|---|
| Serwer | uruchomić z parserem rozumowania (np. vLLM `--reasoning-parser` odpowiednim dla modelu), żeby odpowiedź zawierała rozumowanie w osobnym polu (np. `reasoning_content`), a nie w treści |
| Aplikacja | przy budowaniu kolejnej tury dodawać do historii tylko treść odpowiedzi asystenta, bez pola z rozumowaniem |
| Szablon czatu | sprawdzić, czy szablon modelu sam usuwa bloki myślenia z wcześniejszych tur (w części szablonów Qwen tak jest); jeśli tak, wystarczy nie wklejać ich ręcznie do treści |
| gpt-oss | rozumowanie w osobnym kanale (analysis), odpowiedź w kanale final; do historii kolejnych tur przekazywać tylko final |
| Wyjątek: pętla narzędzi | w obrębie jednej tury z wieloma wywołaniami narzędzi zachować rozumowanie do końca tej tury (model planuje kolejne kroki); usuwać dopiero po odpowiedzi końcowej |

Skutek dla KV cache:

```
Tura 1:  [system][pytanie 1][myślenie 1][odpowiedź 1]
Tura 2:  [system][pytanie 1][odpowiedź 1][pytanie 2]
          └─ z cache ─┘└──── przeliczone od miejsca różnicy ────┘
```

Koszt: krótki prefill od miejsca usunięcia rozumowania. Zysk: brak tysięcy tokenów myślenia w każdej kolejnej turze (krótszy prefill, mniejszy KV cache, więcej miejsca na równoległe zapytania).

Zwalnianie pamięci cache po stronie serwera zwykle nie jest potrzebne (usuwanie automatyczne, LRU). Ręczne czyszczenie jest możliwe w niektórych runtime'ach (np. sloty w llama.cpp), ale służy raczej testom i pomiarom niż normalnej pracy.

## 11. Źródła

| Dane | Źródło |
|---|---|
| Przepustowość i RAM M5 Pro / M5 Max | https://support.apple.com/126318 |
| Przepustowość M5 (bazowy) | https://apple.com/macbook-pro/specs |
| Qwen3-Coder-Next (80B / 3B aktywnych, 256k) | https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF |
| gpt-oss, Gemma 4, Qwen3.5 (przegląd) | https://www.contextstudios.ai/guides/best-open-weight-llms-2026 |
| Gemma 4, Qwen3.6-35B-A3B, Qwen3.5 122B | https://pinggy.io/blog/top_5_local_llm_tools_and_models/ |
| Qwen3.6-27B, Qwen3.6-35B-A3B (otwarte wagi) | https://docs.apiyi.com/en/news/qwen-3-6-opensource-launch |
| Qwen3.6-35B-A3B (architektura, licencja, kontekst) | https://openrouter.ai/models/qwen/qwen3.6-35b-a3b |
| Qwen3.8 (2.4T-A95B) | https://runtimewire.com/article/alibaba-qwen38-24t-open-weights-enterprise-license |
| Qwen3.8-Flash-Next (125B + 51B, 6B aktywnych) | https://gigazine.net/gsc_news/en/20260827-qwen3-8-flash-next/ |
| Qwen3.8-Flash-Next (rozmiary FP8/NVFP4, licencja) | https://atomic.chat/models/qwen3-8-flash-next |
| Qwen3.8-27B | https://www.datalearner.com/en/benchmark-compare/qwen3-8-27b/qwen3-8-flash-next |
