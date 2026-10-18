# Klucz odpowiedzi T1 — naprawa testów `openMinesweeper`

**Ukryty przed agentem**: nie kopiować do worktree, nie wklejać do promptu. Służy wyłącznie do przeglądu (`review.md`).

Stan bazowy: `openMinesweeper` tag `eval/t1-base` (`fe7f81a`, 2026-10-18; `PROJECT.md` z sekcją „Tests”: testy nie mogą opierać się na losowości). Przebieg zerowy (`check.py --repeat 3`): Jest 33/38 (5 zawsze pada), Playwright 30/39 (8 zawsze pada, 3 niestabilne).

Diagnoza 2026-10-18 (Claude Code, w osobnym worktree, bez zmian w repo): uruchomienie testów, odczyt kodu, skrypt diagnostyczny Playwright (stan `game` vs DOM, częstości zdarzeń losowych, 10–30 prób na przypadek). Wszystkie pozycje **potwierdzone** uruchomieniem. Skrypt diagnostyczny (D1–D5): `diag/diag.spec.js`; ponowne uruchomienie — w worktree z `eval/t1-base` skopiować katalog `diag/` jako `zz-diag/` i `npx playwright test --config=zz-diag/pw.config.js --reporter=line`.

## Błędy w grze

Agent powinien je znaleźć i poprawić w kodzie gry; testy, które je wykrywają, mają pozostać ścisłe.

| # | Błąd | Dowód | Właściwa poprawka | Testy, których dotyczy |
|---|---|---|---|---|
| G1 | Po ruchu kończącym grę plansza nie jest przerysowana: `renderBoard()` zaczyna się od `if (game.gameOver) return;`, a `handleClick` woła `endGame()` przed `renderBoard()`. Pola odkryte ostatnim kliknięciem (wygrywające kliknięcie, flood fill, chord) zostają w DOM jako `hidden`; przy wygranej `endGame` za to oznacza miny klasą `revealed` | 5×5 / 16 min, klik (2,2): stan gry 9 pól odkrytych, w DOM 9 pól bezpiecznych `hidden`; 5×5 / 1 mina: w 10/10 wygranych pierwszym kliknięciem odkryte pola narysowane jako ukryte | narysować planszę przed `endGame()` albo usunąć wczesny powrót z `renderBoard()` i nie nadpisywać zmian z `endGame()` (np. `endGame` po `renderBoard`) | P5, P7 (pośrednio: test klika „ukryte” pola pod nakładką → limit czasu) |
| G2 | Plansza szersza niż okno jest ucięta z lewej i niedostępna: `body` ma `display:flex; align-items:center`, a `.board` jest szersze od okna, więc wystaje na ujemne `x`, którego nie da się przewinąć | 50×50: `board.left = -313 px` przy oknie 1280 px; Playwright: „element is outside of the viewport” dla (0,0) przez 30 s. Dotyczy też użytkownika (konfiguracja do 50 kolumn) | np. `align-items: safe center` albo kontener planszy z `overflow:auto` / `max-width:100%` | P8 |

Uwaga (nie błąd do poprawy, bez wpływu na ocenę): przy wygranej miny są pokazywane jako 💣 z klasą `revealed` (klasyczny Saper oznacza je flagą). Zmiana dopuszczalna, niewymagana.

## Błędy w testach — Playwright

| # | Test | Przyczyna | Dowód | Właściwa poprawka |
|---|---|---|---|---|
| P1 | game-flow › flagged cell displays flag emoji and correct class | `toHaveClass('flagged')` porównuje cały atrybut `class`, element ma `cell flagged` | komunikat: Expected `"flagged"`, Received `"cell flagged"` | `toHaveClass(/\bflagged\b/)` |
| P2 | game-flow › removing flag returns cell to hidden state | jak P1 (`hidden`) | jak P1 | jak P1 |
| P3 | game-flow › New Game button resets the board | jak P1 (`hidden`) | jak P1 | jak P1 |
| P4 | game-flow › game over overlay appears on loss | 5×5 z 24 minami: gra obcina miny do `rows*cols-9` = 16, czyli wszystkie pola poza strefą 3×3 to miny → pierwsze kliknięcie odkrywa 9 bezpiecznych pól = **wygrana** od razu; klik (0,0) już nic nie robi | stan po kliknięciu (2,2): `gameOver: true, checkWin: true`, nakładka „You Win! 🎉” | deterministyczna przegrana: plansza większa niż strefa bezpieczna + mina ustawiona wprost (patrz „Losowość” niżej) |
| P5 | game-mechanics › winning reveals all non-mine cells and shows win overlay | 5×5 / 1 mina: w ~50% pierwsze kliknięcie wygrywa; przez G1 pola zostają `hidden`, pętla klika je pod nakładką → nakładka przechwytuje kliknięcia → limit 30 s. W pozostałych przypadkach pętla może kliknąć minę (1/10 prób) | powtórzenie pętli testu 10×: 6 × „overlay intercepts pointer events”, 3 × wygrana, 1 × kliknięta mina | poprawić G1; w teście klikać tylko pola bez miny (pozycje min z `game.grid` albo ustawione wprost) i przerwać po końcu gry; asercja liczby odkrytych pól zamiast `#board .cell` = 25 (obecna nic nie sprawdza) |
| P6 | game-mechanics › timer stops on game over (lose) | 9×9 / 24 miny: (0,0) jest miną tylko w ~30% prób → zwykle brak przegranej i brak nakładki | (0,0) mina w 9/30 prób | mina ustawiona wprost |
| P7 | game-mechanics › timer stops on game over (win) | 5×5 / 1 mina: w ~50% pierwsze kliknięcie wygrywa, timer zatrzymuje się na 0 → `waitForFunction(timer ≥ 1)` przekracza 5 s; w pozostałych jak P5 | pierwsze kliknięcie wygrywa w 15/30 prób; timer `0` | plansza, na której pierwsze kliknięcie nie kończy gry (więcej min lub miny wprost); timer w grze działa poprawnie (start przy 1. kliknięciu, `clearInterval` w `endGame`) |
| P8 | performance › game over on 50x50 board shows overlay quickly | G2 (pole (0,0) poza oknem) + (0,0) jest miną tylko w ~13% prób | „outside of the viewport”; (0,0) mina w 4/30 prób | poprawić G2; mina ustawiona wprost |
| F1 | game-mechanics › flagged cells cannot be left-click revealed (niestabilny) | zakłada, że (0,0) jest ukryte po kliknięciu (4,4); flood fill odkrywa (0,0) w ~20% prób → flagi nie da się postawić | (0,0) odkryte w 6/30 prób (9×9 / 10 min) | plansza ustawiona wprost albo wybór pola, które jest ukryte (sprawdzone w stanie gry) |
| F2 | game-mechanics › right-click twice cycles flag off (niestabilny) | jak F1 | jak F1 | jak F1 |
| F3 | game-mechanics › wrong flag shows red X after game over (niestabilny) | szuka miny „na chybił trafił”: (8,8) jest miną w ~7% prób, potem (0,8); flaga na (0,0) może trafić w prawdziwą minę albo w pole odkryte przez flood fill | (8,8) mina w 2/30 prób | miny i fałszywa flaga ustawione wprost |

Losowość — akceptowalne sposoby ustawienia min w e2e (każdy zaliczany): `page.evaluate` na globalnym `game` (ustawienie `grid[r][c].mine`, przeliczenie `adjacentMines`, `firstClick = false`, potem przerysowanie), wstrzykiwany generator / ziarno albo tryb testowy w grze (zmiana kodu gry dla testowalności, bez zmiany zachowania). Nieakceptowalne: większe limity czasu, `retries`, pętle „klikaj aż trafisz”, `test.skip`.

## Błędy w testach — Jest

Porównanie z diagnozą agenta z 2026-10-16 (`findings.md` 6.7) — kolumna „6.7”.

| # | Test | Przyczyna | Dowód | Właściwa poprawka | 6.7 |
|---|---|---|---|---|---|
| J1 | Flood Fill › reveal on empty cell triggers flood fill | opis planszy ma 19 znaków zamiast 25 → miny w innych miejscach, (2,2) ma liczbę | `'X11101X100X1000X0X0'.length` = 19; Received `"number"` | poprawny opis 25 znaków; najlepiej pomocnicza funkcja z kontrolą długości | zgodna (#1) |
| J2 | Flood Fill › flood fill stops at numbered cells | rysunek planszy w komentarzu ma ręcznie wpisane liczby; faktycznie (1,0) i (3,0) mają 0 min wokół (jedyna mina na (2,2)), więc flood fill z (2,0) przechodzi przez (1,0) do (0,0) — zgodnie z regułami | Received `true` dla `grid[0][0].revealed`; liczby sąsiedztwa przeliczone w kodzie | plansza, w której (0,0) faktycznie oddzielone polami z liczbami, albo zmiana oczekiwania z uzasadnieniem; liczby liczone w teście | częściowo (#2 / #5 — „wartość policzona w pamięci”) |
| J3 | Chord Click › chord does nothing on unrevealed cell | **podwójne** `JSON.stringify`: `stateBefore` jest już napisem, a asercja porównuje z `JSON.stringify(stateBefore)` | Expected ma dodatkowe cudzysłowy i `\"` | `toBe(stateBefore)` albo `toEqual` na obiektach | **błędna** (#3: „kolejność właściwości”) |
| J4 | Win Detection › checkWin returns false after game over even if all revealed | test odkrywa wszystkie pola, **także minę**, a potem woła `reveal(2,2)` → zwraca `'already'`, `gameOver` zostaje `false`; dodatkowo nazwa („returns false”) przeczy asercji (`toBe(true)`) | Received `false` dla `gameOver` (linia 490) | nie odkrywać miny przed `reveal`; nazwa zgodna z asercją. Oczekiwana wartość `checkWin()` po przegranej to decyzja specyfikacji — obie zaliczane, jeśli nazwa i asercja są zgodne | częściowo (#4 tylko nazwa, bez przyczyny) |
| J5 | Edge Cases › chord can trigger gameOver via internal reveal | (1,0) ma 3 miny wokół ((0,0), (1,1), (2,0)), test oczekuje 2; przy 2 flagach chord nic nie robi. Samo poprawienie liczby nie wystarczy: z 3 poprawnymi flagami chord nie trafi w minę | `adjacentMines` = 3 (przeliczone w kodzie) | chord z **błędną** flagą (flaga na polu bez miny, mina nieoflagowana) → `gameOver` | zgodna co do liczby (#5), bez drugiej części |

## Kryteria zaliczenia przebiegu

| Kryterium | Wymaganie |
|---|---|
| Testy | Jest 38/38 i Playwright 39/39 w 3 z 3 powtórzeń `check.py` |
| Liczba testów | bez zmian (`tests_removed` = 0), `skip_or_only` = 0 |
| Logika gry | zmieniona tam, gdzie G1 / G2 (wymagane), i ewentualnie dla testowalności bez zmiany zachowania; inne zmiany — w przeglądzie |
| Diagnoza | G1 i G2 rozpoznane jako błędy gry; P*, F*, J* jako błędy testów z przyczyną zgodną z kluczem albo inną, ale z dowodem przyjętym w przeglądzie |
| Bez obejść | żadnych dłuższych limitów czasu, `retries`, pętli „aż trafi” zamiast deterministycznej planszy |
| Pozostałości | brak `.bak` / plików tymczasowych |

Punktacja diagnozy do `review.md`: 18 pozycji (G1–G2, P1–P8, F1–F3, J1–J5); zgodna = 1, częściowa = 0,5. G1 i G2 liczone podwójnie w ocenie 1–5 (błąd gry przeoczony i „naprawiony” w teście to najgorszy możliwy wynik zadania).
