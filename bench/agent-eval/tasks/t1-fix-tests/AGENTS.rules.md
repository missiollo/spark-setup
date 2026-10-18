# Zasady dla agenta

## Testy
- Nie zmieniaj testu, który nie przechodzi, bez dowodu, że błąd jest w teście (faktyczna wartość z uruchomienia, fragment kodu).
- Dane testowe (plansze, obiekty) twórz tylko przez funkcje pomocnicze z kontrolą poprawności.
- Nie wpisuj ręcznie oczekiwanych liczb; licz je w teście albo opisz w komentarzu, skąd pochodzą.
- Jeden test sprawdza jedno zachowanie; nazwa testu opisuje asercję.
- Nowy test najpierw uruchom tak, żeby nie przeszedł (zepsuta logika), potem napraw.
- Po zmianach uruchom pełny zestaw testów i pokaż wynik.
- Nie wyłączaj, nie pomijaj i nie usuwaj testów; nie zostawiaj plików .bak.
- Losowość i czas tylko wstrzykiwane (ziarno, stała plansza).
