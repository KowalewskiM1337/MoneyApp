# MoneyApp

Temat: Aplikacja ma ułatwiać rozliczanie się między użytkownikami. Przykładowo po wspólnym wyjściu np. na miasto, jeden użytkownik może utworzyć grupę, po czym dodać do niej swoich znajomych i ustalić kto, komu i ile powinien oddać pieniędzy za wyjście. Celem jest prosta i intuicyjna aplikacja.

Zespół: Michał Kowalewski (KowalewskiM1337), Martyna Oleszczuk (@hisumii)

Podział:
- Michał: Szata graficzna (HTML + CSS), Backend (Python), Baza danych (SQL)
- Martyna: Backend (Python), Frontend (React)

Technologia: HTML + CSS + Python (FastAPI) + SQLite + React (Vite) + Docker Compose

## Funkcje

- **Co robi użytkownik**:
  - Tworzy grupę oraz przełącza się między grupami lub usuwa wybraną grupę
  - Dodaje i usuwa uczestników grupy
  - Zapisuje rozliczenie (kto, komu, jaka kwota oraz opcjonalny tytuł)
  - Edytuje istniejące rozliczenia, oznacza je jako rozliczone (przechodzą do historii) lub usuwa
  - Sprawdza automatyczne podsumowanie sald (kto komu łącznie ile ma oddać po zbilansowaniu)
- **Widok**: Jednostronicowy interfejs React oparty na przejrzystym układzie kart (uczestnicy, formularz rozliczenia, podsumowanie sald, historia zobowiązań) oraz oknach modalnych.
- **Dane**: Relacyjna baza SQLite (`groups`, `members`, `debts`) przechowywana w trwałym wolumenie Dockera.

## Uruchomienie przez Docker Compose (zalecane)

Wymagany uruchomiony **Docker Desktop**. W głównym katalogu projektu wykonaj:

```bash
docker compose up --build
```

Po zbudowaniu aplikacja jest dostępna pod adresami:
- **Frontend (aplikacja)**: http://localhost:8080
- **Backend API (dokumentacja Swagger)**: http://localhost:8000/docs

Zatrzymanie kontenerów:

```bash
docker compose down
```

## Uruchomienie lokalne (bez Dockera)

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
2. **Frontend** (w drugim terminalu):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Frontend uruchomi się pod adresem http://localhost:5173 (zapytania `/api` są przekierowywane do portu `8000`).
