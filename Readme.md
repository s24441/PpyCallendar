# Projekt PPY
Kalendarz Python
## Autor
Andrzej Michalecki, s24441, gr. 14c - Zaoczne
### Opis
Zadanie polega na stworzeniu aplikacji konsolowej kalendarza, która ułatwi zarządzanie wydarzeniami poprzez tworzenie, przeglądanie, wyszukiwanie, edycję oraz usuwanie zadań. Ponadto każde wydarzenie może mieć listę kroków do wykonania Kalendarz powinien być trwały tj. zapisywać swój stan do pliku.
### Wymagania:
1. Aplikacja powinna umożliwiać interaktywne przeglądanie kalendarza dzień po dniu poczynając od dnia najbliższego dzisiejszemu.
2. Przeglądanie powinno odbywać się poprzez nawigację strzałkami: lewo – poprzedni element, prawo – następny element, góra – powrót do wyższego poziomu, dół – zejście na niższy poziom. 
3. Podczas przeglądania powinno być możliwe: dodawanie, edycja i usuwanie – dat, wydarzeń i kroków (w zależności od poziomu na którym się akurat znajdujemy).
4. Każdy poziom powinien posiadać priorytet (niski, normalny, wysoki).
5. Edycja powinna pozwalać, w zależności od poziomu:
   * Dla dat: zmianę daty i priorytetu
   * Dla wydarzeń: zmianę godziny, nazwy wydarzenia i priorytetu
   * Dla kroków: zmianę daty i priorytetu
6. Jeżeli któryś z poziomów zawiera elementy zawierające wyższy priorytet, ów wyższy priorytet powinien być propagowany wzwyż, aby od razu było widać, że dany dzień lub wydarzenie zawiera elementy o wyższym priorytecie. Oryginalny priorytet powinien być pamiętany i w razie potrzeby, gdyby dany poziom przestał zawierać elementy o wyższym priorytecie, przywrócony.
7. Aplikacja powinna walidować daty i godziny.
8. Aplikacja powinna pozwalać na wyszukanie wielu elementów po wyrażeniu: dacie, nazwie wydarzenia lub kroku w wydarzeniu.
9. Aplikacja powinna pozwalać również na usunięcie wielu elementów, po wyrażeniu (również dacie, nazwie wydarzenia lub kroku), z zapytaniem przy usunięciu każdego z nich.
10. Aplikacja powinna wyświetlać odpowiednie komunikaty o błędach.
### Informacje dodatkowe:
* Implementacja interaktywnego przeglądania kalendarza będzie wykorzystywać bibliotekę pynput.
* Obsługa dat i czasu w aplikacji będzie wykorzystywać bibliotekę datetime.