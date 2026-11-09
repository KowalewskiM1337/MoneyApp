import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Zezwolenie na zapytania (Strona wyświetla błędy bez tego)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

DB_NAME = 'moneyapp.db'



# Utworzenie połączenia z bazą
def get_db():
    new_connection = sqlite3.connect(DB_NAME)
    new_connection.row_factory = sqlite3.Row # Zapewnia że wyniki to słownik (do łatwiejszego formatowania i zbierania danych)
    return new_connection


# Automatycznie utworzenie tabeli przy uruchomieniu
with get_db() as new_connection:
    new_connection.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_from TEXT,
            debt_to TEXT,
            amount REAL,
            title TEXT
        )
    """)


# Endpointy


# Pobieranie wszystkich długów
@app.get("/api/debts")
def get_debts():
    with get_db() as new_connection:
        rows = new_connection.execute('SELECT * FROM debts').fetchall()
        return [dict(row) for row in rows]

# Dodanie nowego długu
@app.get("/api/debts")
def add_debt(data: dict):
    with get_db() as new_connection:
        cursor = new_connection.execute(
            "INSERT INTO debts (debt_from, debt_to, amount, title) VALUES (?, ?, ?, ?)", # Zamieniam na znaki ?, bo zwykły fstring jest podatny na SQLInjection
            (
                data.get('debt_from'),
                data.get('debt_to'),
                data.get('amount'),
                data.get('title', ''),
            ),
        )
        new_id = cursor.lastrowid
        return {'id': new_id, 'message': 'Dodano wydatek'}

# Usunięcie długu, za pomocą ID
@app.delete("/api/debts/{debt_id}")
def delete_debt(debt_id: int):
    with get_db() as new_connection:
        new_connection.execute('DELETE FROM debts WHERE id = ?', (debt_id,))
        return {'message': 'Usunieto'}