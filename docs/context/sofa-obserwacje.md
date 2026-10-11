---
title: SOFA — obserwacje dotyczące funkcjonalności
date: 2026-10-10
language: pl
tags: [sofa, rag, enterprise-architect, wymagania, analiza-brakow, text-to-sql, raporty, dgx-spark, poc]
related: [llm-pamiec-wzor.md, rag-ea-symulator.html]
---

# SOFA — obserwacje dotyczące funkcjonalności

Notatki robocze do PoC. Dokument zbiera obserwacje i propozycje, nie decyzje.

## Spis treści

**Część I: Koncepcja**
1. [Cel i zakres](#1-cel-i-zakres)
2. [Dostęp do wiedzy z modelu EA: wektorowy RAG vs zapytania strukturalne](#2-dostęp-do-wiedzy-z-modelu-ea-wektorowy-rag-vs-zapytania-strukturalne)
3. [Architektura hybrydowa](#3-architektura-hybrydowa)

**Część II: Funkcjonalność**

4. [Analiza braków](#4-analiza-braków)
5. [Text-to-SQL i raporty](#5-text-to-sql-i-raporty)

**Część III: Realizacja techniczna**

6. [Repozytorium EA: punkty zaczepienia](#6-repozytorium-ea-punkty-zaczepienia)
7. [Narzędzia dla modelu (tool calling)](#7-narzędzia-dla-modelu-tool-calling)
8. [Budowa promptu](#8-budowa-promptu)
9. [Sprzęt i wydajność](#9-sprzęt-i-wydajność)

**Część IV: Plan PoC**

10. [Proponowana kolejność wdrażania](#10-proponowana-kolejność-wdrażania)
11. [Metryki](#11-metryki)
12. [Otwarte pytania](#12-otwarte-pytania)

**Zakończenie**

13. [Podsumowanie i wnioski](#13-podsumowanie-i-wnioski)

---

# Część I: Koncepcja

## 1. Cel i zakres

| Obszar | Opis |
|---|---|
| Cel PoC | analiza jakości wymagań, RAG nad modelami Enterprise Architect (EA), analiza zapytań analityków biznesowych w celu ulepszania narzędzia |
| Dane | rzeczywiste, niejawne artefakty projektowe |
| Produkt docelowy | aplikacja webowa w środowisku deweloperskim jako playground dla analityków biznesowych |
| Platforma | wniosek o DGX Spark |
| Zakres dokumentu | jak model językowy ma korzystać z wiedzy w modelach EA, jak zrealizować analizę braków, text-to-SQL i raporty, co z tego wynika dla promptów, sprzętu i planu PoC |

## 2. Dostęp do wiedzy z modelu EA: wektorowy RAG vs zapytania strukturalne

| Cecha | Wektorowy RAG | Zapytanie strukturalne |
|---|---|---|
| Źródło | tekst wyciągnięty z modelu EA (raporty, dokumenty, XMI) | repozytorium EA wprost (baza z elementami, pakietami, relacjami) |
| Mechanizm | podobieństwo znaczeniowe (embeddingi) | dokładne zapytanie po strukturze (SQL / graf) |
| Wynik | top-k najbardziej podobnych fragmentów | pełna, dokładna lista |
| Do modelu trafia | dużo tekstu (tysiące tokenów) | tylko wynik (setki tokenów) |
| Kompletność | brak gwarancji (top-k) | gwarantowana |
| Mocna strona | pytania o treść | pytania o strukturę: braki, liczności, pokrycie, zależności |
| Słaba strona | pytania o brak relacji, agregacje, "wszystkie" | pytania o znaczenie i sformułowania |

### 2.1 Dlaczego wektorowy RAG nie nadaje się do pytań o strukturę

Przykład: "Które wymagania w pakiecie »Kontrola graniczna« nie mają przypisanego komponentu realizującego?"

| Problem | Wyjaśnienie |
|---|---|
| Braku nie da się zembeddować | Wektor opisuje treść fragmentu, nie to, czego w modelu nie ma |
| Top-k nie gwarantuje kompletności | Przy 200 wymaganiach i top-k = 10 model nie znajdzie wszystkich luk |
| Model sam sprawdza relacje w tekście | Wolno (długi prefill) i podatne na pomyłki |

## 3. Architektura hybrydowa

| Typ pytania | Ścieżka | Przykład |
|---|---|---|
| Struktura (przewidziana) | gotowe narzędzie | wymagania bez komponentu realizującego; pokrycie pakietu |
| Struktura (nieprzewidziana) | text-to-SQL (sekcja 5) | "ile wymagań o priorytecie wysokim zmieniono w ostatnim miesiącu, wg pakietów?" |
| Treść | wektorowy RAG | "znajdź wymagania dotyczące biometrii" |
| Jakość wymagań w pakiecie | SQL wybiera dokładną listę, LLM ocenia treść porcjami | ocena jednoznaczności, mierzalności, kompletności sformułowań |

Ostatni wiersz to rdzeń SOFA: struktura wybiera dokładnie te elementy, które trzeba ocenić, a LLM robi to, w czym jest dobry, czyli ocenę sformułowań.

### 3.1 Rola LLM

| Krok | Opis |
|---|---|
| 1. Zrozumienie pytania | Klasyfikacja (struktura / treść / jakość) i wybór narzędzia lub ścieżki text-to-SQL |
| 2. Wywołanie narzędzia | Narzędzie wykonuje zapytanie, zwraca wynik |
| 3. Interpretacja | Streszczenie, sugestie, ocena treści zwróconych elementów |

### 3.2 Gotowe zapytania vs text-to-SQL

| Podejście | Zalety | Wady | Rola w PoC |
|---|---|---|---|
| Sparametryzowane narzędzia (gotowe zapytania) | przewidywalne, testowalne, bezpieczne | ograniczone do przewidzianych pytań | fundament; typowe pytania i analiza braków |
| Text-to-SQL (model pisze SQL) | elastyczne, pytania ad hoc, raporty | ryzyko cichych błędów, wymaga walidacji | druga ścieżka, na warstwie semantycznej i z walidacją (sekcja 5) |

Oba podejścia się uzupełniają: zweryfikowane zapytania z text-to-SQL mogą stawać się nowymi gotowymi narzędziami lub raportami.

Konto bazy danych: tylko odczyt.

---

# Część II: Funkcjonalność

## 4. Analiza braków

Zasada: nie pytać modelu otwarcie "czego tu brakuje?" dla całego modelu EA, bo taka odpowiedź jest niekompletna i niepowtarzalna. Brak trzeba zawsze zdefiniować względem czegoś: reguły, kryterium albo listy kontrolnej.

### 4.1 Trzy rodzaje braków

| Rodzaj braku | Względem czego | Mechanizm | Rola LLM | Powtarzalność |
|---|---|---|---|---|
| Strukturalny | reguły modelowania | SQL na repozytorium | brak lub wyjaśnienie wyniku | pełna |
| Treściowy (w pojedynczym wymaganiu) | kryteria jakości wymagań | LLM ocenia każde wymaganie | główna | wysoka przy ustrukturyzowanym wyjściu |
| Pokrycia (obszar nieopisany wcale) | lista kontrolna obszarów | odwrócone wyszukiwanie + LLM | ocena pokrycia | średnia–wysoka |

### 4.2 Warstwa 1: braki strukturalne (katalog reguł)

| Reguła | Opis | Waga (propozycja) |
|---|---|---|
| Wymaganie bez realizacji | brak relacji `Realisation` z komponentu | wysoka |
| Komponent-sierota | komponent nie realizuje żadnego wymagania | średnia |
| Wymaganie bez testu | brak śladu do przypadku testowego | wysoka |
| Brak atrybutów | brak priorytetu, źródła, statusu (tagged values) | średnia |
| Pusta notatka | wymaganie bez opisu | wysoka |
| Niespójny status | zatwierdzone wymaganie realizowane przez komponent w statusie draft | średnia |
| Duplikaty | te same lub bardzo podobne nazwy | niska |

Reguły jako konfiguracja, nie kod:

```yaml
- id: GAP-001
  name: Wymaganie bez komponentu realizującego
  severity: high
  scope: Requirement
  sql: find_unrealized_requirements.sql
- id: GAP-004
  name: Wymaganie bez priorytetu
  severity: medium
  scope: Requirement
  sql: missing_tagged_value.sql
  params: { tag: Priority }
```

Przykładowe zapytanie dla GAP-001: sekcja [6.1](#61-przykład-wymagania-bez-komponentu-realizującego).

### 4.3 Warstwa 2: braki treściowe (ocena każdego wymagania)

| Krok | Opis |
|---|---|
| 1 | Struktura wybiera dokładną listę wymagań (np. cały pakiet, rekurencyjnie) |
| 2 | LLM ocenia wymagania porcjami według jawnych kryteriów (np. ISO/IEC/IEEE 29148) |
| 3 | Wynik ustrukturyzowany (JSON): ocena per kryterium, uzasadnienie, propozycja poprawki |

Przykładowe kryteria: jednoznaczność, weryfikowalność, pojedynczość (jedno wymaganie = jedna potrzeba), brak sformułowań nieprecyzyjnych ("szybko", "intuicyjnie", "w razie potrzeby"), obecność mierzalnej wartości.

Przykładowy format wyniku:

```json
{
  "id": "REQ-112",
  "criteria": {
    "unambiguous": { "score": "fail", "reason": "Słowo 'szybko' bez wartości" },
    "verifiable": { "score": "fail", "reason": "Brak kryterium akceptacji" },
    "singular": { "score": "pass" }
  },
  "suggestion": "System weryfikuje dokument w czasie nie dłuższym niż 3 s dla 95% przypadków."
}
```

Charakter obciążenia: wiele krótkich wywołań, więc dobry przypadek dla batchingu (vLLM).

### 4.4 Warstwa 3: braki pokrycia (odwrócone wyszukiwanie)

Zamiana pytania "czego brakuje?" na serię pytań "czy jest X?".

| Krok | Opis |
|---|---|
| 1 | Lista kontrolna obszarów, które system tej klasy powinien mieć opisane |
| 2 | Dla każdej pozycji: wyszukiwanie wektorowe wymagań potencjalnie ją pokrywających |
| 3 | LLM ocenia pokrycie: pełne / częściowe / brak, z uzasadnieniem |
| 4 | Brak trafień lub ocena "brak" = luka |

Przykładowe pozycje listy kontrolnej (do uzgodnienia z analitykami):

| Obszar | Przykładowe pytanie kontrolne |
|---|---|
| Audyt i logowanie zdarzeń | Czy określono, jakie zdarzenia są rejestrowane i jak długo? |
| Ochrona danych osobowych | Czy opisano podstawę przetwarzania, minimalizację, retencję? |
| Kontrola dostępu | Czy zdefiniowano role i uprawnienia? |
| Dostępność | Czy podano wymagany poziom dostępności i okna serwisowe? |
| Obsługa błędów | Czy opisano zachowanie przy awarii zależnych systemów? |
| Retencja i archiwizacja | Czy określono okresy przechowywania danych? |

Lista kontrolna jest jednocześnie produktem PoC (skodyfikowana wiedza ekspercka).

### 4.5 Przepływ i model wyników

```
reguły SQL ────────────┐
ocena treści (LLM) ────┼──► tabela ustaleń
pokrycie (wektory+LLM) ┘          │
                                  ▼
                   raport dla analityka (web app)
                   + link do elementu w EA
                   + oznaczenie "fałszywy alarm"
```

Wspólny format ustalenia:

| Pole | Opis |
|---|---|
| run_id | identyfikator przebiegu analizy |
| layer | strukturalny / treściowy / pokrycia |
| rule_id | np. GAP-001, QUAL-UNAMBIGUOUS, COV-AUDIT |
| element_id | ID elementu EA (lub obszar listy kontrolnej przy braku pokrycia) |
| severity | wysoka / średnia / niska |
| reason | uzasadnienie |
| suggestion | propozycja poprawki (opcjonalnie) |
| feedback | ocena analityka: trafne / fałszywy alarm |

### 4.6 Elementy zwiększające wartość

| Element | Wartość |
|---|---|
| Wspólna tabela ustaleń | filtrowanie, sortowanie po wadze, eksport niezależnie od źródła |
| Historia przebiegów | trend (np. luk w pakiecie z 40 do 12) jako argument przy ocenie PoC |
| Pętla zwrotna analityków | kalibracja reguł i progów; uzupełnia analizę zapytań analityków |
| Link do elementu w EA | szybkie przejście do poprawki |

## 5. Text-to-SQL i raporty

Cel: analityk zadaje pytanie o model w języku naturalnym, model generuje SQL do repozytorium EA, a wynik można zapisać jako powtarzalny raport.

### 5.1 Dlaczego EA to korzystny przypadek

| Cecha | Znaczenie |
|---|---|
| Stały, udokumentowany schemat | każde repozytorium EA ma te same tabele; schemat nie musi być odkrywany per projekt |
| Wąska domena | kilkanaście pojęć (wymagania, komponenty, pakiety, relacje, atrybuty) zamiast setek tabel biznesowych |
| Powtarzalne pytania | szybko powstaje biblioteka zweryfikowanych zapytań |

### 5.2 Pułapki

| Pułapka | Opis | Mitygacja |
|---|---|---|
| Generyczne kolumny | wszystko w `t_object`; typ w `Object_Type` / `Stereotype`; nieczytelne `PDATA1..5` | warstwa semantyczna (widoki) |
| Tagged values jako klucz–wartość | priorytet, status itd. to wiersze w `t_objectproperties`, nie kolumny | widoki "spłaszczające" atrybuty |
| Rekurencja pakietów | "w pakiecie X" zwykle oznacza też podpakiety | widok drzewa pakietów (`v_package_tree`) |
| Ciche błędy | zapytanie działa poprawnie, ale odpowiada na inne pytanie | interpretacja przed wynikiem, zestaw testowy, feedback |

### 5.3 Poziomy dojrzałości

| Poziom | Opis | Niezawodność | Realne w PoC (8 tygodni) |
|---|---|---|---|
| 1. Gotowe narzędzia | sparametryzowane zapytania (`find_unrealized_requirements` itd.) | pełna | tak |
| 2. Warstwa semantyczna | model pisze SQL na czytelnych widokach (`v_requirements`, `v_relations`, `v_package_tree`), nie na `t_object` | wysoka dla typowych pytań | tak |
| 3. Walidacja i pętla naprawcza | parsowanie SQL, lista dozwolonych widoków, tylko `SELECT`, `LIMIT`, timeout; przy błędzie model poprawia zapytanie | wysoka, bez katastrof | tak |
| 4. Biblioteka zweryfikowanych zapytań | zatwierdzone pary pytanie → SQL; podobne przykłady trafiają do promptu jako few-shot | rośnie z czasem | początek |
| 5. Katalog raportów | zatwierdzone zapytania jako parametryzowane, wersjonowane raporty, uruchamiane na żądanie lub cyklicznie | pełna (deterministyczne) | wersja podstawowa |

Poziom 2 daje najwięcej: wiedza o specyfice EA jest zaszyta raz, w widokach, a model pisze proste zapytania w języku domeny.

Przykładowe widoki warstwy semantycznej (propozycja):

| Widok | Zawartość |
|---|---|
| `v_requirements` | wymagania z ID, nazwą, opisem, pakietem, statusem, priorytetem (spłaszczone tagged values) |
| `v_components` | komponenty z pakietem, statusem |
| `v_relations` | relacje: źródło, cel, typ (czytelne nazwy typów) |
| `v_package_tree` | pakiety z pełną ścieżką i przodkami (rekurencja rozwiązana) |

### 5.4 Ograniczanie cichych błędów

| Mechanizm | Opis |
|---|---|
| Interpretacja przed wynikiem | np. "Rozumiem: wymagania w pakiecie Kontrola graniczna i podpakietach, bez relacji Realisation z komponentu. Wynik: 7 wierszy." |
| Widoczny SQL | rozwijany podgląd zapytania dla chętnych do weryfikacji |
| Zestaw testowy (golden set) | 30–50 typowych pytań z oczekiwanymi wynikami; automatyczny test po każdej zmianie modelu, promptu lub widoków |
| Feedback analityków | ocena trafne / nietrafne; zasila bibliotekę zapytań (poziom 4) |

### 5.5 Raporty: ad hoc vs zatwierdzone

| Cecha | Ad hoc | Raport zatwierdzony |
|---|---|---|
| Źródło | pytanie → text-to-SQL | zapisane, zweryfikowane zapytanie |
| Powtarzalność | może się różnić między uruchomieniami | identyczna |
| Zastosowanie | eksploracja, pytania jednorazowe | cykliczne przeglądy, trendy, raporty dla kierownictwa |

Przepływ: pytanie → SQL → weryfikacja przez analityka → "zapisz jako raport" → parametryzacja (np. pakiet, data) → katalog raportów.

Zasada: liczby i tabele zawsze pochodzą z SQL, nigdy z LLM. Model może dodać streszczenie i komentarz (np. "najwięcej luk w podpakiecie X").

Formaty wyniku: tabela w aplikacji webowej, eksport CSV / XLSX / MD.

### 5.6 Bezpieczeństwo i audyt

| Element | Opis |
|---|---|
| Konto bazy | tylko odczyt; brak DDL i DML |
| Limity | limit wierszy, timeout zapytania |
| Zakres | lista dozwolonych widoków |
| Log zapytań | pytanie, wygenerowany SQL, wynik, ocena; audyt i jednocześnie materiał do analizy zapytań analityków |
| Model lokalny | dane niejawne nie opuszczają środowiska |

### 5.7 Sprzęt i model

| Obserwacja | Konsekwencja |
|---|---|
| Opis widoków to kilka tysięcy tokenów, stały | trafia do prefix cache |
| Wyniki zapytań są krótkie | krótki prefill; scenariusz możliwy do prototypowania na M4 Pro 48 GB |
| Generowanie SQL to zadanie "kodowe" | dobre modele: Qwen3-Coder-Next (Spark), Qwen3.8-27B (laptop) |

---

# Część III: Realizacja techniczna

## 6. Repozytorium EA: punkty zaczepienia

| Element | Gdzie |
|---|---|
| Format plikowy | .qea (SQLite); wersje serwerowe na SQL Server, PostgreSQL i innych |
| Elementy (wymagania, komponenty, ...) | `t_object` (`Object_Type`, `Stereotype`, `Name`, `Note`) |
| Pakiety | `t_package` (hierarchia przez `Parent_ID`) |
| Relacje | `t_connector` (`Start_Object_ID`, `End_Object_ID`, `Connector_Type`) |
| Tagged values | `t_objectproperties` |
| Diagramy | `t_diagram`, `t_diagramobjects` |

Do weryfikacji na własnym repozytorium: dokładne wartości `Object_Type`, `Connector_Type` (np. `Realisation`), używane stereotypy i tagged values.

### 6.1 Przykład: wymagania bez komponentu realizującego

```sql
SELECT o.Object_ID, o.Name
FROM t_object o
JOIN t_package p ON o.Package_ID = p.Package_ID
WHERE o.Object_Type = 'Requirement'
  AND p.Name = 'Kontrola graniczna'
  AND NOT EXISTS (
    SELECT 1 FROM t_connector c
    JOIN t_object s ON c.Start_Object_ID = s.Object_ID
    WHERE c.End_Object_ID = o.Object_ID
      AND c.Connector_Type = 'Realisation'
      AND s.Object_Type = 'Component'
  );
```

Podpakiety wymagają zapytania rekurencyjnego (`WITH RECURSIVE` po `t_package.Parent_ID`) albo widoku `v_package_tree` (sekcja 5.3).

## 7. Narzędzia dla modelu (tool calling)

| Narzędzie | Parametry | Zwraca | Typ pytania | Zastosowanie |
|---|---|---|---|---|
| `list_requirements` | package, recursive | lista wymagań (ID, nazwa, status) | struktura | braki: warstwa 1, 2 (wybór listy) |
| `get_element` | id | pełne dane elementu (nazwa, notatka, tagged values) | treść | braki: warstwa 2 |
| `get_relations` | id, depth, connector_type | powiązane elementy | struktura | braki: warstwa 1 |
| `find_unrealized_requirements` | package, recursive | wymagania bez komponentu realizującego | struktura | braki: warstwa 1 |
| `find_orphans` | object_type, package | elementy bez żadnych relacji | struktura | braki: warstwa 1 |
| `trace_coverage` | package | pokrycie: wymaganie → komponent → (test) | struktura | braki: warstwa 1 |
| `count_by_type` | package | liczności elementów wg typu i statusu | struktura | braki: warstwa 1; raporty |
| `find_missing_tagged_values` | object_type, tag | elementy bez wymaganego atrybutu (np. priorytet, kryterium akceptacji) | struktura / jakość | braki: warstwa 1 |
| `search_elements_semantic` | text, top_k, package | najbardziej podobne elementy (wektorowo) | treść | braki: warstwa 3 |
| `assess_requirement_quality` | ids | ocena jakości sformułowań (LLM, porcjami) | jakość | braki: warstwa 2 |
| `run_sql` | sql | wynik zapytania na widokach (po walidacji) | struktura (ad hoc) | text-to-SQL |
| `run_report` | report_id, params | wynik zapisanego raportu | struktura | raporty |
| `save_report` | name, sql, params | zapis zweryfikowanego zapytania jako raportu | — | raporty |

## 8. Budowa promptu

### 8.1 Kolejność sekcji (prefix caching)

| Kolejność | Sekcja | Zmienność |
|---|---|---|
| 1 | System prompt: rola, kryteria oceny jakości wymagań | stała |
| 2 | Definicje narzędzi | stała |
| 3 | Opis schematu EA / widoków semantycznych i słownik (typy elementów, relacji, konwencje ID) | stała |
| 4 | Przykłady few-shot (w tym zweryfikowane pary pytanie → SQL) | stała / rzadko zmieniana |
| 5 | Kontekst pakietu / projektu | półstała |
| 6 | Wyniki narzędzi / fragmenty RAG (sortowane po ID) | per pytanie |
| 7 | Historia rozmowy (skrócona) | rośnie |
| 8 | Pytanie analityka | nowa |

Nic zmiennego (data, użytkownik, ID sesji) na początku promptu.

### 8.2 Ograniczanie tokenów

| Technika | Przykład |
|---|---|
| Zwarty format elementów | `REQ-112 \| Weryfikacja dokumentu \| pakiet: Kontrola graniczna \| realizuje: –` |
| Bez GUID-ów | krótkie ID zamiast `{3F2504E0-...}` |
| Chunking po elemencie (dla RAG) | 1 element + relacje 1. stopnia = 1 fragment |
| Reranker | wyszukaj 30, przekaż 5–8 |
| Deduplikacja | element tylko raz |
| Instrukcje po angielsku | treść modeli w oryginale |
| Zapytania strukturalne zamiast RAG | dla pytań o strukturę prompt ma setki zamiast tysięcy tokenów |

## 9. Sprzęt i wydajność

| Obserwacja | Konsekwencja dla SOFA |
|---|---|
| Wektorowy RAG = długie prompty (10k+ tokenów) | prefill dominuje czas do pierwszego tokena (TTFT) |
| Prefill zależy od mocy obliczeniowej, decode od przepustowości | DGX Spark: najkrótszy TTFT; Maki: szybki decode, wolny prefill |
| Zapytania strukturalne i text-to-SQL skracają prompt do setek / kilku tysięcy tokenów | mniejsze wymagania sprzętowe dla pytań o strukturę |
| Ocena jakości wielu wymagań = wiele wywołań | przepustowość serwowania (batching w vLLM) ważniejsza niż prędkość pojedynczej odpowiedzi |
| Playground dla wielu analityków | potrzebne serwowanie równoległe (vLLM na Sparku) |
| Modele MoE | krótszy prefill i szybszy decode jednocześnie |

Szczegóły i liczby: `llm-pamiec-wzor.md` (sekcje 4–10), symulacja: `rag-ea-symulator.html`.

### 9.1 Argumenty do wniosku o DGX Spark

| Argument | Uzasadnienie |
|---|---|
| Charakter obciążenia | RAG i ocena treści = długie prompty = potrzeba mocnego prefillu |
| Wielu użytkowników | dojrzały stos serwowania (CUDA, vLLM, TensorRT-LLM) |
| Większe modele | 128 GB, FP4: modele klasy ~120B (np. gpt-oss-120b) z zapasem na kontekst; Qwen3-Coder-Next do text-to-SQL |
| Rozważane alternatywy | Strix Halo (taniej, słabszy prefill, mniej dojrzały stos); Mac z dużą pamięcią (szybki decode, wolny prefill) |
| Wstępny prototyp | możliwy na M4 Pro 48 GB (np. Qwen3.6-35B-A3B + bge-m3; Qwen3.8-27B do SQL) |
| Dodatkowa wartość dla zespołu | ten sam serwer (vLLM) może obsługiwać lokalnego asystenta programistycznego (OpenCode, sekcja 9.2) |

### 9.2 Asystent programistyczny: OpenCode

OpenCode (opencode.ai) to otwartoźródłowy agent programistyczny (terminal, IDE, aplikacja desktopowa), działający podobnie jak Claude Code: czyta, edytuje i uruchamia kod w repozytorium. Model jest kwestią konfiguracji: chmura, Ollama, LM Studio albo własny endpoint zgodny z API OpenAI.

| Cecha | Znaczenie dla SOFA |
|---|---|
| Niezależność od dostawcy modelu | można używać wyłącznie modeli lokalnych; kod i dane nie opuszczają środowiska |
| Routing modeli do zadań | np. eksploracja kodu na szybkim MoE, trudniejsze zmiany na mocniejszym modelu |
| Tryb serwerowy (`opencode serve`) | bezgłowy serwer HTTP z API; możliwa integracja z innymi narzędziami |

Scenariusze użycia:

| Scenariusz | Konfiguracja | Uwagi |
|---|---|---|
| Budowa prototypu SOFA na laptopie | OpenCode + Ollama / LM Studio na M4 Pro 48 GB (Qwen3.6-35B-A3B do eksploracji, Qwen3.8-27B do trudniejszych zmian) | narzędzie do pisania kodu PoC (widoki SQL, narzędzia, web app) |
| Wspólny asystent kodu na DGX Spark | vLLM serwuje Qwen3-Coder-Next jako endpoint zgodny z OpenAI; OpenCode u członków zespołu wskazuje na ten endpoint | offline, bez kosztów API; dodatkowy argument do wniosku o Sparka |
| Iteracja nad widokami i zapytaniami SQL | agent pracuje w repozytorium z definicjami widoków, regułami (YAML) i zestawem testowym | uruchamia testy golden set po każdej zmianie |

Uwagi praktyczne:

| Uwaga | Opis |
|---|---|
| Tool calling | małe modele (rzędu 7B) często źle obsługują protokół narzędzi; wybierać modele z dobrym tool callingiem |
| Okno kontekstu | domyślne ustawienia runtime'ów bywają małe (np. 4096 tokenów); agent potrzebuje kilkudziesięciu tysięcy, więc trzeba je podnieść (np. `num_ctx` w Ollamie) |
| Licencje | nie podpinać pod backend płatnej subskrypcji (narusza warunki dostawcy); używać modeli lokalnych lub własnych kluczy API |
| Polityki IT | na komputerze służbowym sprawdzić, czy instalacja i uruchamianie agenta z dostępem do terminala jest dozwolone |

### 9.3 Porównanie modeli: gpt-oss-120b vs Qwen3.8-27B

#### Różnice konstrukcyjne

| Cecha | gpt-oss-120b | Qwen3.8-27B |
|---|---|---|
| Architektura | MoE, 117 mld (5.1 mld aktywnych) | dense, 27 mld (wszystkie aktywne) |
| Wagi | ~63 GB (MXFP4) | ~16 GB (Q4) / ~22 GB (Q6) |
| Kontekst | 128K | 262K |
| Wejście | tylko tekst | tekst + obraz (+ wideo) |
| Języki | trenowany głównie na angielskim | silna wielojęzyczność (rodzina Qwen) |
| Tool calling, ekosystem | bardzo dobre wsparcie, dojrzałe narzędzia | dobre |
| Rozumowanie | poziomy wysiłku (low / medium / high) | tryb thinking |
| Licencja | Apache 2.0 | do sprawdzenia |

#### Szybkość (szacunki z założeń symulatora, do zastąpienia pomiarami)

gpt-oss-120b (na M4 Pro 48 GB nie mieści się):

| Scenariusz | DGX Spark | M3 Max 128 GB |
|---|---|---|
| Decode | ~55 tok/s | ~80 tok/s |
| Prefill 16k (RAG) | ~2 s | ~12 s |
| Prefill 2–4k (text-to-SQL, bez cache) | <1 s | 1.5–3 s |
| Odpowiedź z rozumowaniem (~1000 tokenów) | ~18 s | ~13 s |

Qwen3.8-27B (Q4):

| Scenariusz | DGX Spark | M3 Max 128 GB | M4 Pro 48 GB |
|---|---|---|---|
| Decode | ~10 tok/s | ~15 tok/s | ~10 tok/s |
| Prefill 16k (RAG) | ~11 s | ~1 min | ~1.5–2 min |
| Prefill 2–4k (bez cache) | 1–3 s | 8–15 s | 15–30 s |
| Odpowiedź z rozumowaniem (~1000 tokenów) | ~1.5 min | ~1 min | ~1.5 min |

Obserwacje:
- Oba modele "myślą" przed odpowiedzią; przy gęstym modelu (~10–15 tok/s) każde 1000 tokenów rozumowania to ok. 1–1.5 min. Prefix caching pomaga na prefill, nie na decode.
- M3 Max ma najszybszy decode (400 GB/s), ok. 1.5× szybciej niż Spark; Spark ma ok. 6× szybszy prefill.
- Przy krótkich promptach (ścieżka strukturalna, text-to-SQL) liczy się głównie decode, więc różnice między platformami maleją, a M3 Max wypada najlepiej.
- Oba modele mieszczą się razem na M3 Max (~79 z 96 GB), ale z małym zapasem na KV cache; na Sparku jest więcej miejsca.

#### Jakość w zadaniach SOFA (oczekiwania do weryfikacji zestawem testowym)

| Zadanie | gpt-oss-120b | Qwen3.8-27B | Uwagi |
|---|---|---|---|
| Text-to-SQL na widokach | dobry | prawdopodobnie lepszy (nowsza generacja, mocny w kodzie) | prompty krótkie, więc wolniejszy decode mniej boli |
| Wybór i wywołanie narzędzi | bardzo dobry, przewidywalny | dobry | przewaga dojrzałości ekosystemu gpt-oss |
| RAG nad treścią EA po polsku | poprawny, angielskocentryczny | lepsze rozumienie polskiego | istotne dla nazw, opisów i niuansów sformułowań |
| Ocena jakości wymagań (PL) | dobry przy jawnych kryteriach | lepszy w niuansach językowych | zadanie wsadowe, czas mniej krytyczny |
| Diagramy EA jako obrazy | niemożliwe | możliwe | opcja: ocena diagramów ze zrzutów |
| Generowanie kodu aplikacji | dobry | dobry | do kodu na Sparku lepszy Qwen3-Coder-Next |
| Ocena wsadowa wielu wymagań | ~5× tańszy obliczeniowo na token | droższy | przy batchingu liczy się moc obliczeniowa |

Brak publicznych benchmarków dla tych konkretnych zadań (SQL na schemacie EA, polskie wymagania); rozstrzygnie zestaw testowy (sekcja 5.4) uruchomiony na obu modelach.

#### Proponowany podział ról modeli

| Rola | Model | Uzasadnienie |
|---|---|---|
| Czat interaktywny, routing, tool calling | gpt-oss-120b (lub Qwen3.6-35B-A3B) | szybki decode, krótkie TTFT |
| Text-to-SQL | do rozstrzygnięcia testem: Qwen3.8-27B vs gpt-oss-120b | jakość SQL ważniejsza niż sekundy |
| Ocena jakości wymagań (wsadowo, PL) | Qwen3.8-27B | jakość językowa; czas mniej krytyczny |
| Asystent kodu (OpenCode) | Qwen3-Coder-Next | wyspecjalizowany i szybki |

Na Sparku wszystkie role mieszczą się jednocześnie (~63 + ~16 GB + KV cache < ~112 GB). Na M4 Pro do prototypu: Qwen3.6-35B-A3B jako szybki model główny, Qwen3.8-27B do SQL i oceny jakości.

Opcja do przetestowania: Qwen3.8-Flash-Next (6 mld aktywnych, szybkość zbliżona do gpt-oss, w benchmarkach Qwena lepszy od 3.8-27B), ale na Sparku tylko w niskiej kwantyzacji, bez miejsca na drugi model, licencja inna niż Apache 2.0.

#### Wnioski z porównania platform

| Platforma | Najlepsze zastosowanie |
|---|---|
| M3 Max 128 GB | jednoosobowe prototypowanie i porównywanie modeli; ścieżka strukturalna i czat (najszybszy decode) |
| DGX Spark | narzędzie zespołowe: długi kontekst RAG, ocena wsadowa z batchingiem, wielu analityków równocześnie (vLLM) |
| M4 Pro 48 GB | prototyp z mniejszymi modelami (Qwen3.6-35B-A3B, Qwen3.8-27B) |

---

# Część IV: Plan PoC

## 10. Proponowana kolejność wdrażania

| Etap | Zakres | Uzasadnienie |
|---|---|---|
| 0 | Prototyp lokalny (M4 Pro 48 GB): dostęp do repozytorium EA, widoki semantyczne, kilka narzędzi strukturalnych, mały model; porównanie modeli (gpt-oss-120b vs Qwen3.8-27B) na M3 Max 128 GB na danych syntetycznych | potwierdzenie podejścia i wyboru modeli przed uzyskaniem sprzętu |
| 1 | Warstwa strukturalna analizy braków (katalog reguł SQL) | szybka, pewna, natychmiastowy efekt; nie wymaga dużego modelu |
| 2 | Text-to-SQL na widokach z walidacją + zestaw testowy pytań | elastyczne pytania ad hoc; mierzalna dokładność |
| 3 | Warstwa treściowa (ocena jakości wymagań) | rdzeń SOFA; korzysta z batchingu na Sparku |
| 4 | Warstwa pokrycia (lista kontrolna + odwrócone wyszukiwanie) | wymaga uzgodnienia listy kontrolnej z analitykami |
| 5 | Playground dla analityków (web app): katalog raportów, zbieranie zapytań i feedbacku | dane do ulepszania narzędzi, reguł i biblioteki zapytań |

## 11. Metryki

| Metryka | Po co |
|---|---|
| TTFT (osobno dla ścieżki strukturalnej, text-to-SQL i RAG) | odczuwalna szybkość dla analityka |
| Tokeny/s (decode) | czas pełnej odpowiedzi |
| Długość promptu (tokeny) | wpływ technik z sekcji 8 |
| Trafienia prefix cache | skuteczność kolejności sekcji |
| Kompletność wyników strukturalnych | porównanie z ręcznym zapytaniem |
| Dokładność text-to-SQL na zestawie testowym | wiarygodność odpowiedzi ad hoc |
| Dokładność i czas odpowiedzi per model (ten sam zestaw testowy) | wybór modelu dla każdej roli (sekcja 9.3) |
| Odsetek zapytań poprawionych w pętli naprawczej | jakość generowania SQL i widoków |
| Liczba zapytań zapisanych jako raporty | użyteczność dla analityków |
| Zgodność oceny jakości z ekspertem | wartość merytoryczna |
| Rozkład typów pytań analityków | które narzędzia dodać; które pytania trafiają do RAG |
| Liczba ustaleń per warstwa i waga | skala braków w modelach |
| Odsetek fałszywych alarmów (feedback analityków) | jakość reguł i oceny LLM |
| Trend ustaleń między przebiegami | czy narzędzie realnie poprawia modele |

## 12. Otwarte pytania

| Obszar | Pytanie |
|---|---|
| Dostęp do danych | Jaki backend repozytorium EA jest używany (plik .qea czy serwer bazodanowy) i czy możliwy jest dostęp tylko do odczytu? |
| Model danych | Jakie typy elementów, relacji, stereotypy i tagged values są faktycznie używane? |
| Widoki | Czy można utworzyć widoki w bazie repozytorium, czy trzeba je budować w osobnej bazie (kopia / replika)? |
| Kryteria jakości | Jakie kryteria jakości wymagań przyjąć (np. ISO/IEC/IEEE 29148, wewnętrzne wytyczne)? |
| Śledzenie | Czy w modelach są ślady do testów (trace coverage wymaganie → test)? |
| Aktualność | Jak często zmienia się model (częstotliwość reindeksacji dla RAG)? |
| Lista kontrolna | Kto i jak uzgodni listę kontrolną obszarów dla analizy pokrycia? |
| Reguły | Jakie wagi przypisać regułom strukturalnym i czy analitycy mają już nieformalne checklisty do wykorzystania? |
| Zestaw testowy | Kto przygotuje 30–50 typowych pytań analityków z oczekiwanymi wynikami? |
| Raporty | Jakie raporty analitycy przygotowują dziś ręcznie i które warto zautomatyzować w pierwszej kolejności? |

---

# Zakończenie

## 13. Podsumowanie i wnioski

### 13.1 Najważniejsze wnioski

| Nr | Wniosek |
|---|---|
| 1 | Model EA to dane strukturalne, a nie tylko tekst. Pytania o strukturę (braki relacji, pokrycie, liczności) należy obsługiwać zapytaniami do repozytorium, nie wektorowym RAG. |
| 2 | Wektorowy RAG zostaje dla pytań o treść oraz, w odwróconej formie, dla analizy pokrycia względem listy kontrolnej. |
| 3 | Rdzeń SOFA to połączenie: struktura wybiera dokładną listę elementów, LLM ocenia ich treść według jawnych kryteriów. |
| 4 | Brak zawsze definiujemy względem czegoś: reguły, kryterium lub listy kontrolnej. Otwarte "czego brakuje?" daje wyniki niekompletne i niepowtarzalne. |
| 5 | Analiza braków ma trzy warstwy (strukturalna, treściowa, pokrycia) zapisujące wyniki do wspólnej tabeli ustaleń z feedbackiem analityków i historią przebiegów. |
| 6 | Gotowe narzędzia są fundamentem, a text-to-SQL drugą ścieżką dla pytań nieprzewidzianych. Kluczem do jego dojrzałości jest warstwa semantyczna (widoki), walidacja i zestaw testowy. |
| 7 | Zweryfikowane zapytania text-to-SQL stają się raportami. Liczby w raportach zawsze pochodzą z SQL, nigdy z LLM. |
| 8 | Log zapytań (pytanie, SQL, wynik, ocena) służy jednocześnie do audytu i do analizy zapytań analityków. |
| 9 | Kolejność sekcji promptu (stałe na początku) i zwarty format elementów EA skracają prefill, czyli czas do pierwszej odpowiedzi. |
| 10 | Obciążenie SOFA (długie prompty RAG, wiele wywołań oceny, wielu użytkowników) przemawia za platformą z mocnym prefillem i dojrzałym serwowaniem, czyli DGX Spark. |

### 13.2 Rekomendowane następne kroki

| Krok | Opis |
|---|---|
| 1 | Uzyskać dostęp tylko do odczytu do repozytorium EA i zweryfikować schemat (typy, relacje, tagged values) |
| 2 | Zaprojektować 3–4 widoki semantyczne (`v_requirements`, `v_relations`, `v_package_tree`, ...) |
| 3 | Zbudować pierwsze 3–5 reguł strukturalnych i uruchomić je na jednym pakiecie |
| 4 | Zebrać z analitykami 30–50 typowych pytań jako zestaw testowy dla text-to-SQL |
| 5 | Zrobić prototyp lokalny na M4 Pro (widoki, narzędzia strukturalne, text-to-SQL) jako materiał do wniosku; do budowy kodu użyć OpenCode z lokalnym modelem |
| 6 | Porównać gpt-oss-120b i Qwen3.8-27B na zestawie testowym (dane syntetyczne, M3 Max 128 GB); zmierzone TFLOPS i tok/s wpisać do symulatora |
| 7 | Ustalić z analitykami kryteria jakości wymagań i wstępną listę kontrolną obszarów |
| 8 | Uzupełnić wniosek o DGX Spark o argumenty z sekcji 9.1, porównanie z sekcji 9.3 i pomiary z prototypu |
