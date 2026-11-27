"""Database operations for the expense tracker."""
from __future__ import annotations

import datetime as dt
import math
import sqlite3
from pathlib import Path

FIELDS = ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode")
GROUP_SQL = {
    "Payment method": "Mode",
    "Payee": "Payee",
    "Category": "Category",
    "Month": "strftime('%Y-%m', Date)",
}


class ExpenseStore:
    def __init__(self, database: str | Path = "expenses.db") -> None:
        self.conn = sqlite3.connect(str(database))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ExpenseLog (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT, Payee TEXT, Description TEXT,
                Category TEXT, Amount REAL, Mode TEXT
            )
        """)
        self.conn.commit()

    @staticmethod
    def _validated(date: str, payee: str, description: str, category: str,
                   amount: float, mode: str) -> tuple:
        try:
            dt.date.fromisoformat(date)
        except (TypeError, ValueError) as exc:
            raise ValueError("Enter a valid date (YYYY-MM-DD).") from exc
        payee, description, category, mode = (
            str(value).strip() for value in (payee, description, category, mode)
        )
        if not all((payee, description, category, mode)):
            raise ValueError("All expense details are required.")
        try:
            amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise ValueError("Enter a valid amount.") from exc
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be a positive finite number.")
        return date, payee, description, category, amount, mode

    def add(self, date: str, payee: str, description: str, category: str,
            amount: float, mode: str) -> int:
        values = self._validated(date, payee, description, category, amount, mode)
        with self.conn:
            cursor = self.conn.execute("""
                INSERT INTO ExpenseLog (Date, Payee, Description, Category, Amount, Mode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, values)
        return int(cursor.lastrowid)

    def update(self, record_id: int, date: str, payee: str, description: str,
               category: str, amount: float, mode: str) -> bool:
        values = self._validated(date, payee, description, category, amount, mode)
        with self.conn:
            cursor = self.conn.execute("""
                UPDATE ExpenseLog SET Date=?, Payee=?, Description=?, Category=?,
                Amount=?, Mode=? WHERE ID=?
            """, (*values, int(record_id)))
        return cursor.rowcount > 0

    def delete(self, record_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM ExpenseLog WHERE ID=?", (int(record_id),))
        return cursor.rowcount > 0

    def clear(self) -> int:
        with self.conn:
            cursor = self.conn.execute("DELETE FROM ExpenseLog")
        return cursor.rowcount

    def get(self, record_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM ExpenseLog WHERE ID=?", (int(record_id),)).fetchone()
        return dict(row) if row else None

    def list_expenses(self, search: str = "") -> list[dict]:
        term = search.strip()
        if term:
            # Treat % and _ as ordinary characters in the search box.
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = self.conn.execute("""
                SELECT * FROM ExpenseLog
                WHERE Payee LIKE ? ESCAPE '\\' OR Description LIKE ? ESCAPE '\\'
                   OR Category LIKE ? ESCAPE '\\' OR Mode LIKE ? ESCAPE '\\'
                   OR Date LIKE ? ESCAPE '\\'
                ORDER BY ID DESC
            """, (f"%{escaped}%",) * 5).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM ExpenseLog ORDER BY ID DESC").fetchall()
        return [dict(row) for row in rows]

    def total(self) -> float:
        return float(self.conn.execute("SELECT COALESCE(SUM(Amount), 0) FROM ExpenseLog").fetchone()[0])

    def summary(self, group_by: str) -> list[tuple[str, float]]:
        expression = GROUP_SQL.get(group_by)
        if expression is None:
            raise ValueError("Unsupported reporting group.")
        rows = self.conn.execute(
            f"SELECT {expression}, SUM(Amount) FROM ExpenseLog "
            f"GROUP BY {expression} ORDER BY SUM(Amount) DESC"
        ).fetchall()
        return [(str(row[0] or "Unknown"), float(row[1])) for row in rows]

    def close(self) -> None:
        self.conn.close()
