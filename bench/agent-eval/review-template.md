# Przegląd przebiegu {{name}}

Wypełnia człowiek po przebiegu, z kluczem odpowiedzi zadania (`tasks/<zadanie>/answer-key.md`) obok. Wynik przeglądu przepisać do kolumn `review_score` i `interventions` w `results-<zadanie>.csv`.

## Diagnoza (każda pozycja z klucza)

| Pozycja klucza | Diagnoza agenta | Zgodna? (tak / częściowo / nie) | Poprawka właściwa? | Uwagi |
|---|---|---|---|---|

## Zmiany

| Pytanie | Odpowiedź |
|---|---|
| Czy asercje osłabiono (np. `toBe` → `toBeTruthy`, dłuższe limity czasu bez przyczyny)? | |
| Czy logikę gry zmieniono tylko tam, gdzie klucz wskazuje błąd gry? | |
| Zmiany poza zakresem zadania | |
| Czy raport końcowy agenta zgadza się z faktycznym wynikiem `check.json`? | |

## Przebieg

| Pytanie | Odpowiedź |
|---|---|
| Interwencje człowieka (liczba, opis) | |
| Pętle / powtarzanie tych samych kroków | |
| Ucięte odpowiedzi (`truncated` w `run.json`) | |

## Ocena 1–5

| Ocena | Znaczenie |
|---|---|
| 5 | wszystkie pozycje klucza poprawnie, zmiany do przyjęcia bez poprawek |
| 4 | drobne poprawki przed przyjęciem |
| 3 | połowa pozycji poprawnie albo istotne poprawki |
| 2 | pojedyncze poprawne pozycje; więcej pracy przy przeglądzie niż przy samodzielnej poprawce |
| 1 | szkodliwe (osłabione testy, zepsuta gra) albo brak wyniku |

Ocena: 
Uzasadnienie: 
