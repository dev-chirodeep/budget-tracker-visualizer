"""Store expenses and monthly budgets in a local SQLite database."""
from __future__ import annotations

from datetime import date as Date
import math
from pathlib import Path
import sqlite3

FIELDS = ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode")
GROUP_SQL = {
    "Payment method": "Mode",
    "Payee": "Payee",
    "Category": "Category",
    "Month": "strftime('%Y-%m', Date)",
}


class ExpenseStore:
    def __init__(self, database: str | Path = "expenses.db") -> None:
        self.database = Path(database).expanduser().resolve()
        self.conn = sqlite3.connect(str(self.database))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ExpenseLog (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT, Payee TEXT, Description TEXT,
                Category TEXT, Amount REAL, Mode TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS MonthlyBudget (
                Month TEXT PRIMARY KEY, Amount REAL NOT NULL
            )
        """)
        self.conn.commit()

    @staticmethod
    def _valid_expense(date: str, payee: str, description: str, category: str,
                       amount: float | str, mode: str) -> tuple:
        try:
            Date.fromisoformat(date)
        except (ValueError, TypeError) as exc:
            raise ValueError("Use a valid date in YYYY-MM-DD format.") from exc
        payee, description, category, mode = (
            str(value).strip() for value in (payee, description, category, mode)
        )
        if not all((payee, description, category, mode)):
            raise ValueError("Please complete all expense fields.")
        try:
            amount = float(amount)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Enter a valid amount.") from exc
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be greater than zero.")
        return (date, payee, description, category, amount, mode)

    def add(self, date: str, payee: str, description: str, category: str,
            amount: float | str, mode: str) -> int:
        values = self._valid_expense(date, payee, description, category, amount, mode)
        with self.conn:
            cur = self.conn.execute("""
                INSERT INTO ExpenseLog (Date, Payee, Description, Category, Amount, Mode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, values)
        return int(cur.lastrowid)

    def update(self, record_id: int, date: str, payee: str, description: str,
               category: str, amount: float | str, mode: str) -> bool:
        values = self._valid_expense(date, payee, description, category, amount, mode)
        with self.conn:
            cur = self.conn.execute("""
                UPDATE ExpenseLog SET Date=?, Payee=?, Description=?, Category=?,
                Amount=?, Mode=? WHERE ID=?
            """, (*values, int(record_id)))
        return cur.rowcount > 0

    def delete(self, record_id: int) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM ExpenseLog WHERE ID=?", (int(record_id),))
        return cur.rowcount > 0

    def clear(self) -> int:
        with self.conn:
            cur = self.conn.execute("DELETE FROM ExpenseLog")
        return cur.rowcount

    def get(self, record_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM ExpenseLog WHERE ID=?", (int(record_id),)).fetchone()
        return dict(row) if row is not None else None

    def list_expenses(self, search: str = "", *, date_from: str = "", date_to: str = "",
                      category: str = "", mode: str = "", min_amount: str = "",
                      max_amount: str = "") -> list[dict]:
        filters, params = [], []
        term = search.strip()
        if term:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            filters.append("(" + " OR ".join(
                f"{col} LIKE ? ESCAPE '\\'" for col in ("Payee", "Description", "Category", "Mode", "Date")) + ")")
            params.extend([f"%{escaped}%"] * 5)
        for value, sql in ((date_from, "Date >= ?"), (date_to, "Date <= ?")):
            if value.strip():
                try:
                    Date.fromisoformat(value.strip())
                except ValueError as exc:
                    raise ValueError("Dates must use YYYY-MM-DD.") from exc
                filters.append(sql)
                params.append(value.strip())
        if date_from.strip() and date_to.strip() and date_from > date_to:
            raise ValueError("The start date must be before the end date.")
        for value, column in ((category, "Category"), (mode, "Mode")):
            if value and value != "All":
                filters.append(f"{column} = ?")
                params.append(value)
        for value, op in ((min_amount, ">="), (max_amount, "<=")):
            if str(value).strip():
                try:
                    number = float(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Enter valid amount filters.") from exc
                if not math.isfinite(number) or number < 0:
                    raise ValueError("Amount filters must be non-negative.")
                filters.append(f"Amount {op} ?")
                params.append(number)
        sql = "SELECT * FROM ExpenseLog"
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        rows = self.conn.execute(sql + " ORDER BY Date DESC, ID DESC", params).fetchall()
        return [dict(row) for row in rows]

    def total(self) -> float:
        return float(self.conn.execute("SELECT COALESCE(SUM(Amount),0) FROM ExpenseLog").fetchone()[0])

    def summary(self, group_by: str) -> list[tuple[str, float]]:
        expression = GROUP_SQL.get(group_by)
        if expression is None:
            raise ValueError("Unsupported report type.")
        rows = self.conn.execute(
            f"SELECT {expression}, SUM(Amount) FROM ExpenseLog "
            f"GROUP BY {expression} ORDER BY SUM(Amount) DESC").fetchall()
        return [(str(row[0] or "Unknown"), float(row[1])) for row in rows]

    @staticmethod
    def _valid_month(month: str) -> str:
        try:
            Date.fromisoformat(month + "-01")
        except ValueError as exc:
            raise ValueError("Month must use YYYY-MM.") from exc
        if len(month) != 7:
            raise ValueError("Month must use YYYY-MM.")
        return month

    def set_budget(self, month: str, amount: float | str | None) -> None:
        month = self._valid_month(month)
        if amount is None or amount == "":
            with self.conn:
                self.conn.execute("DELETE FROM MonthlyBudget WHERE Month=?", (month,))
            return
        try:
            amount = float(amount)
        except (ValueError, TypeError) as exc:
            raise ValueError("Enter a valid monthly budget.") from exc
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Budget must be greater than zero.")
        with self.conn:
            self.conn.execute("""INSERT INTO MonthlyBudget (Month, Amount) VALUES (?, ?)
                ON CONFLICT(Month) DO UPDATE SET Amount=excluded.Amount""", (month, amount))

    def get_budget(self, month: str) -> float | None:
        row = self.conn.execute("SELECT Amount FROM MonthlyBudget WHERE Month=?",
                                (self._valid_month(month),)).fetchone()
        return float(row[0]) if row else None

    def dashboard(self, month: str) -> dict:
        month = self._valid_month(month)
        records = self.conn.execute("""SELECT Date, Category, Amount FROM ExpenseLog
            WHERE substr(Date, 1, 7) = ?""", (month,)).fetchall()
        monthly_total = sum(row["Amount"] for row in records)
        categories = {}
        active_dates = set()
        for row in records:
            categories[row["Category"]] = categories.get(row["Category"], 0.0) + row["Amount"]
            active_dates.add(row["Date"])
        top_category = max(categories, key=categories.get) if categories else "—"
        budget = self.get_budget(month)
        return {
            "month": month,
            "monthly_total": float(monthly_total),
            "all_time_total": self.total(),
            "transaction_count": len(records),
            "top_category": top_category,
            "daily_average": (float(monthly_total) / len(active_dates)) if active_dates else 0.0,
            "budget": budget,
            "budget_remaining": (budget - monthly_total) if budget is not None else None,
        }

    def backup(self, destination: str | Path) -> None:
        destination = Path(destination).expanduser().resolve()
        if destination == self.database:
            raise ValueError("Choose a different file for the backup.")
        with sqlite3.connect(str(destination)) as dest:
            self.conn.backup(dest)

    def restore(self, source: str | Path) -> None:
        source = Path(source).expanduser().resolve()
        if source == self.database:
            raise ValueError("Choose a backup file, not the open database.")
        if not source.is_file():
            raise ValueError("Backup file not found.")
        with sqlite3.connect(str(source)) as backed_up:
            ok = backed_up.execute("PRAGMA quick_check").fetchone()[0]
            cols = [row[1] for row in backed_up.execute("PRAGMA table_info(ExpenseLog)")]
            if ok != "ok" or tuple(cols) != FIELDS:
                raise ValueError("This is not a compatible expense database backup.")
            backed_up.backup(self.conn)
        # Older backups might not contain monthly budgets.
        self.conn.execute("""CREATE TABLE IF NOT EXISTS MonthlyBudget (
            Month TEXT PRIMARY KEY, Amount REAL NOT NULL)""")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()