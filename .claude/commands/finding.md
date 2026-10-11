---
description: Zapisz znalezisko, decyzję lub zadanie w docs/ (findings, decisions, backlog)
argument-hint: krótki opis albo wklejony log
---

Zapisz w dokumentacji repozytorium to, co ustaliliśmy: $ARGUMENTS

Kroki:

1. Ustal z rozmowy i podanego logu: objaw, przyczynę, liczby (tylko z logów lub pomiarów), wniosek, ewentualną decyzję i zadania.
2. `docs/findings.md`: dodaj nową podsekcję w sekcji 3 (kolejny numer 3.x, tytuł z datą RRRR-MM-DD) albo uzupełnij istniejącą, jeśli dotyczy tego samego tematu. Zaktualizuj tabele, których dotyczy zmiana (3, 4.1 porty, 5.1 modele, 5.2 zestawy, 10 rozwiązywanie problemów).
3. `docs/decisions.md`: jeśli zapadła decyzja, dopisz wiersz D-xx (data, decyzja, uzasadnienie, odrzucone alternatywy, odwołanie do sekcji).
4. `docs/backlog.md`: zaktualizuj „Stan”, „Najbliższe drobne kroki” i tabelę kroków; nowe zadania na końcu tabeli Backlog (kolejny numer B-xx); zrobione oznacz, nie usuwaj.
5. Pokaż krótkie podsumowanie zmian (pliki, sekcje) i zaproponuj tytuł commita po angielsku. Nie commituj bez potwierdzenia.

Styl: po polsku, zwięźle, tabele zamiast prozy, bez powtarzania tego, co już jest w dokumentach.
