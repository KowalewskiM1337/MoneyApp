import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MoneyApp API")

#tworzenie apki webowej, pozwolenie jej na tworzenie żądań (get, delete itp.) i różnych nagłówków
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = os.getenv("DB_PATH", "moneyapp.db") #pobranie ścieżki do pliku bazy danych a jesli jej nie ma używanie lokalnego pliku


#modele danych wejściowych
class GroupCreate(BaseModel):
    name: str


class MemberCreate(BaseModel):
    name: str


class DebtPayload(BaseModel):
    debt_from: str
    debt_to: str
    amount: float
    title: Optional[str] = ""


#tworzenie połączenia z bazą SQLite
def get_db():
    db_dir = os.path.dirname(DB_NAME)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True) #tworzene katalogów dla pliku bazy jesli nie istnieja
    conn = sqlite3.connect(DB_NAME) #otwiera polaczenie z baza sqlite
    conn.row_factory = sqlite3.Row #zapytania mzna czytac po nazwie kolumny nie tylko po indeksie
    conn.execute("PRAGMA foreign_keys = ON") #wymusza dzialanie kluczy obcych i usuwania w sqlite
    return conn


#wywolana przy starcie modulu, tworzy tabele (groups, members, debts jesli nie istnieja)
def init_db():
    is_new_db = not os.path.exists(DB_NAME)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                debt_from TEXT NOT NULL,
                debt_to TEXT NOT NULL,
                amount REAL NOT NULL,
                title TEXT DEFAULT '',
                is_settled INTEGER DEFAULT 0,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)

        #przykładowa grupa startowa tylko przy tworzeniu nowej bazy
        if is_new_db:
            cursor = conn.execute(
                "INSERT INTO groups (name) VALUES (?)", ("Wyjście na miasto",)
            )
            gid = cursor.lastrowid
            conn.execute(
                "INSERT INTO members (group_id, name) VALUES (?, ?), (?, ?)",
                (gid, "Koleżanka", gid, "Michał"),
            )
            conn.execute(
                "INSERT INTO debts (group_id, debt_from, debt_to, amount, title, is_settled) VALUES (?, ?, ?, ?, ?, 0)",
                (gid, "Koleżanka", "Michał", 45.50, "za pizzę"),
            )


init_db()


#grupy!!!!!!!

@app.get("/api/groups") #zwraca liste grup posortowana rosnaco po id
def get_groups():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM groups ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]


@app.post("/api/groups") #odrzuca puste nazwy, wrzuca grupe do sqlite
def create_group(payload: GroupCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Podaj nazwę grupy.")
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        return {"id": cursor.lastrowid, "name": name}


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int): #usuwa grupe
    with get_db() as conn:
        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        return {"message": "Usunięto grupę"}


#uczestnicy!!!!!!!!!!

@app.get("/api/groups/{group_id}/members") #pobieranie uczestnikow przypisanych do ich konretnych grup
def get_members(group_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM members WHERE group_id = ? ORDER BY id ASC", (group_id,)
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/groups/{group_id}/members") #spradzanie czy jakis uczestnik sie nie powtarza w grupie jesli tak to odrzuca
def add_member(group_id: int, payload: MemberCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Podaj imię uczestnika.")
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM members WHERE group_id = ? AND LOWER(name) = LOWER(?)",
            (group_id, name),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400, detail="Taki uczestnik już należy do tej grupy."
            )
        cursor = conn.execute(
            "INSERT INTO members (group_id, name) VALUES (?, ?)", (group_id, name)
        )
        return {"id": cursor.lastrowid, "group_id": group_id, "name": name}


@app.delete("/api/members/{member_id}") #sprawdza czy uzytkownik istnieje, sprawdza czy nie ma dlugow przy imieniu, jesli ma to nie mozna usunac
def delete_member(member_id: int): 
    with get_db() as conn:
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?", (member_id,)
        ).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Nie znaleziono uczestnika.")

        #blokada usunięcia osoby z aktywnymi długami w tej grupie
        active_debt = conn.execute(
            """
            SELECT id FROM debts
            WHERE group_id = ? AND is_settled = 0 AND (debt_from = ? OR debt_to = ?)
            LIMIT 1
            """,
            (member["group_id"], member["name"], member["name"]),
        ).fetchone()
        if active_debt:
            raise HTTPException(
                status_code=400,
                detail="Nie można usunąć uczestnika, który ma nierozliczone zobowiązania.",
            )

        conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        return {"message": "Usunięto uczestnika"}


#dlugi!!!!!!!!!!!!

@app.get("/api/groups/{group_id}/debts") #pokazuje jakie dlugi w grupie
def get_debts(group_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM debts WHERE group_id = ? ORDER BY is_settled ASC, id DESC",
            (group_id,),
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/groups/{group_id}/debts") 
def add_debt(group_id: int, payload: DebtPayload):
    debt_from = payload.debt_from.strip()
    debt_to = payload.debt_to.strip() 
    title = (payload.title or "").strip()
    amount = round(float(payload.amount), 2) #zaokragla kwote

    if not debt_from or not debt_to:
        raise HTTPException(status_code=400, detail="Wybierz obie osoby.")
    if debt_from == debt_to:
        raise HTTPException(status_code=400, detail="Wybierz dwie różne osoby.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Kwota musi być większa od zera.")

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO debts (group_id, debt_from, debt_to, amount, title, is_settled)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (group_id, debt_from, debt_to, amount, title),
        )
        return {"id": cursor.lastrowid, "message": "Dodano rozliczenie"}


@app.put("/api/debts/{debt_id}")
def update_debt(debt_id: int, payload: DebtPayload):
    debt_from = payload.debt_from.strip()
    debt_to = payload.debt_to.strip()
    title = (payload.title or "").strip()
    amount = round(float(payload.amount), 2)

    if debt_from == debt_to:
        raise HTTPException(status_code=400, detail="Wybierz dwie różne osoby.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Kwota musi być większa od zera.")

    with get_db() as conn:
        conn.execute(
            """
            UPDATE debts
            SET debt_from = ?, debt_to = ?, amount = ?, title = ?
            WHERE id = ?
            """,
            (debt_from, debt_to, amount, title, debt_id),
        )
        return {"message": "Zaktualizowano rozliczenie"}


@app.patch("/api/debts/{debt_id}/settle")
def toggle_settle_debt(debt_id: int):
    with get_db() as conn:
        conn.execute(
            "UPDATE debts SET is_settled = CASE WHEN is_settled = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (debt_id,),
        )
        return {"message": "Zmieniono status rozliczenia"}


@app.delete("/api/debts/{debt_id}")
def delete_debt(debt_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
        return {"message": "Usunięto wpis"}


#kto komu ma ile oddac!!!!!!!!!!!

@app.get("/api/groups/{group_id}/summary")
def get_summary(group_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT debt_from, debt_to, amount FROM debts WHERE group_id = ? AND is_settled = 0",
            (group_id,),
        ).fetchall()

    #bilans
    balances = {}
    for row in rows:
        balances[row["debt_from"]] = balances.get(row["debt_from"], 0.0) - row["amount"]
        balances[row["debt_to"]] = balances.get(row["debt_to"], 0.0) + row["amount"]

    debtors = [[p, -bal] for p, bal in balances.items() if round(bal, 2) < 0]
    creditors = [[p, bal] for p, bal in balances.items() if round(bal, 2) > 0]

    transfers = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        amount = round(min(debtors[i][1], creditors[j][1]), 2)
        if amount > 0:
            transfers.append(
                {
                    "debt_from": debtors[i][0],
                    "debt_to": creditors[j][0],
                    "amount": amount,
                }
            )
        debtors[i][1] = round(debtors[i][1] - amount, 2)
        creditors[j][1] = round(creditors[j][1] - amount, 2)
        if debtors[i][1] <= 0.001:
            i += 1
        if creditors[j][1] <= 0.001:
            j += 1

    return transfers
