import os
import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="MoneyApp API")

# Zezwolenie na zapytania z frontendu (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = os.getenv("DB_PATH", "moneyapp.db")


# Modele danych wejściowych
class GroupCreate(BaseModel):
    name: str


class MemberCreate(BaseModel):
    name: str


class DebtPayload(BaseModel):
    debt_from: str
    debt_to: str
    amount: float
    title: Optional[str] = ""


# Utworzenie połączenia z bazą SQLite
def get_db():
    db_dir = os.path.dirname(DB_NAME)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Inicjalizacja tabel i danych startowych przy pierwszym uruchomieniu
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

        # Przykładowa grupa startowa tylko przy tworzeniu nowej bazy
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


# --- GRUPY ---

@app.get("/api/groups")
def get_groups():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM groups ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]


@app.post("/api/groups")
def create_group(payload: GroupCreate):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Podaj nazwę grupy.")
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO groups (name) VALUES (?)", (name,))
        return {"id": cursor.lastrowid, "name": name}


@app.delete("/api/groups/{group_id}")
def delete_group(group_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        return {"message": "Usunięto grupę"}


# --- UCZESTNICY GRUPY ---

@app.get("/api/groups/{group_id}/members")
def get_members(group_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM members WHERE group_id = ? ORDER BY id ASC", (group_id,)
        ).fetchall()
        return [dict(row) for row in rows]


@app.post("/api/groups/{group_id}/members")
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


@app.delete("/api/members/{member_id}")
def delete_member(member_id: int):
    with get_db() as conn:
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?", (member_id,)
        ).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Nie znaleziono uczestnika.")

        # Blokada usunięcia osoby z aktywnymi długami w tej grupie
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


# --- ROZLICZENIA (DŁUGI) ---

@app.get("/api/groups/{group_id}/debts")
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
    amount = round(float(payload.amount), 2)

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


# --- PODSUMOWANIE SALD (KTO KOMU ŁĄCZNIE ILE MA ODDAĆ) ---

@app.get("/api/groups/{group_id}/summary")
def get_summary(group_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT debt_from, debt_to, amount FROM debts WHERE group_id = ? AND is_settled = 0",
            (group_id,),
        ).fetchall()

    # Bilans netto każdej osoby: ujemny = musi oddać, dodatni = ma otrzymać
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
