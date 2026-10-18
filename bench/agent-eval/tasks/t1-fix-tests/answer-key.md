# Klucz odpowiedzi T1 — naprawa testów `openMinesweeper`

**Ukryty przed agentem**: nie kopiować do worktree, nie wklejać do promptu. Służy wyłącznie do przeglądu (`review.md`).

Stan wyjściowy (przebieg zerowy `check.py --repeat 3`, 2026-10-18): Jest 33/38 (5 zawsze pada), Playwright 30/39 (8 zawsze pada, 3 niestabilne).

## Pozycje

Status: **potwierdzone** = sprawdzone uruchomieniem; **hipoteza** = do potwierdzenia przed pierwszym przebiegiem; **do ustalenia** = nieznana przyczyna. Klucz musi być kompletny (bez „do ustalenia”) przed przebiegami, które liczymy do raportu.

| # | Test | Przyczyna | Błąd w | Właściwa poprawka | Status |
|---|---|---|---|---|---|
| P1 | game-flow › flagged cell displays flag emoji and correct class | `toHaveClass('flagged')` porównuje cały atrybut, element ma `cell flagged` | teście | `toHaveClass(/\bflagged\b/)` | potwierdzone (komunikat Playwright) |
| P2 | game-flow › removing flag returns cell to hidden state | jak P1 (`hidden`) | teście | jak P1 | potwierdzone |
| P3 | game-flow › New Game button resets the board | jak P1 (`hidden`) | teście | jak P1 | potwierdzone |
| P4 | game-flow › game over overlay appears on loss | miny losowe — kliknięcie nie trafia w minę, gra kończy się wygraną („You Win! 🎉”) | teście (niedeterminizm) | ustawienie min wprost (tryb testowy / wstrzyknięta plansza), nie szukanie miny metodą prób | potwierdzone (komunikat), sposób ustawienia min do ustalenia |
| P5 | game-mechanics › winning reveals all non-mine cells and shows win overlay | | | | do ustalenia |
| P6 | game-mechanics › timer stops on game over (lose) | `waitForSelector` przekracza 5 s | | | do ustalenia |
| P7 | game-mechanics › timer stops on game over (win) | timer nie pokazuje ≥ 1 s w 5 s | | | do ustalenia — możliwy błąd gry (timer nie startuje) |
| P8 | performance › game over on 50x50 board shows overlay quickly | przekroczone 30 s | | | do ustalenia |
| F1 | game-mechanics › flagged cells cannot be left-click revealed | niestabilny | | | do ustalenia |
| F2 | game-mechanics › right-click twice cycles flag off | niestabilny | | | do ustalenia |
| F3 | game-mechanics › wrong flag shows red X after game over | niestabilny | | | do ustalenia |
| J1 | Chord Click › chord does nothing on unrevealed cell | | teście (wg agenta, `findings.md` 6.7) | | hipoteza |
| J2 | Edge Cases › chord can trigger gameOver via internal reveal | `adjacentMines` = 3, test oczekuje 2 — wartość policzona „w pamięci” | teście (wg agenta) | poprawiona plansza albo wartość liczona w teście | hipoteza (komunikat Jest potwierdza 3 ≠ 2) |
| J3 | Flood Fill › flood fill stops at numbered cells | | teście (wg agenta) | | hipoteza |
| J4 | Flood Fill › reveal on empty cell triggers flood fill | | teście (wg agenta) | | hipoteza |
| J5 | Win Detection › checkWin returns false after game over even if all revealed | nazwa „returns false”, asercja `toBe(true)` | teście (wg agenta) | | hipoteza |

## Kryteria zaliczenia przebiegu

| Kryterium | Wymaganie |
|---|---|
| Testy | Jest 38/38 i Playwright 39/39 w 3 z 3 powtórzeń `check.py` |
| Liczba testów | bez zmian (`tests_removed` = 0), `skip_or_only` = 0 |
| Logika gry | zmieniona tylko przy pozycjach z „Błąd w: grze” |
| Diagnoza | każda pozycja zgodna z kluczem albo inna, ale z dowodem przyjętym w przeglądzie |
| Pozostałości | brak `.bak` / plików tymczasowych |
