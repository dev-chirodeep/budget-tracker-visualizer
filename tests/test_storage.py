"""Tests use temporary databases; no personal expenses are touched."""
from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path
from storage import ExpenseStore
from reporting import export_csv, export_excel, export_pdf


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "expenses.db"
        self.store = ExpenseStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def add(self, payee="Cafe", amount=125, date="2026-11-05", category="Food", mode="UPI"):
        return self.store.add(date, payee, "Lunch", category, amount, mode)

    def test_add_edit_delete(self):
        id_ = self.add()
        self.assertEqual(self.store.get(id_)["Payee"], "Cafe")
        self.assertTrue(self.store.update(id_, "2026-11-06", "Bookshop", "Books", "Shopping", 250, "Cash"))
        self.assertEqual(self.store.get(id_)["Amount"], 250)
        self.assertTrue(self.store.delete(id_))
        self.assertIsNone(self.store.get(id_))

    def test_search_literal_wildcards(self):
        self.add("Cafe_10%")
        self.add("CafeA100")
        self.assertEqual(len(self.store.list_expenses("_10%")), 1)
        self.assertEqual(len(self.store.list_expenses("Lunch")), 2)
        self.assertEqual(len(self.store.list_expenses("nonexistent")), 0)

    def test_filters(self):
        self.add("Cafe", 150, "2026-11-05", "Food", "UPI")
        self.add("Shop", 600, "2026-10-09", "Shopping", "Cash")
        self.add("Market", 250, "2026-11-18", "Food", "Cash")
        self.assertEqual(len(self.store.list_expenses(date_from="2026-11-01", date_to="2026-11-30")), 2)
        self.assertEqual(len(self.store.list_expenses(category="Food", mode="UPI")), 1)
        self.assertEqual(len(self.store.list_expenses(min_amount="200", max_amount="500")), 1)
        self.assertEqual(len(self.store.list_expenses(search="Shop", min_amount="300")), 1)

    def test_filter_validation(self):
        for filters in (dict(date_from="invalid"), dict(date_from="2026-12-01", date_to="2026-01-01"),
                        dict(min_amount="-1"), dict(max_amount="inf"), dict(min_amount="str")):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                self.store.list_expenses(**filters)

    def test_amount_validation(self):
        for value in ("", "nope", 0, -2, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.add(amount=value)
        with self.assertRaises(ValueError):
            self.store.add("2026-99-01", "A", "Test", "Food", 5, "UPI")

    def test_reporting(self):
        self.add("Cafe", 100, "2026-11-05", "Food", "UPI")
        self.add("Shop", 200, "2026-10-09", "Shopping", "Cash")
        self.assertEqual(self.store.total(), 300)
        self.assertEqual(self.store.summary("Category"), [("Shopping", 200), ("Food", 100)])
        self.assertEqual(self.store.summary("Month"), [("2026-10", 200), ("2026-11", 100)])
        with self.assertRaises(ValueError):
            self.store.summary("Category; DROP TABLE ExpenseLog")

    def test_monthly_budget(self):
        self.assertIsNone(self.store.get_budget("2026-11"))
        self.store.set_budget("2026-11", 1000)
        self.assertEqual(self.store.get_budget("2026-11"), 1000)
        self.store.set_budget("2026-11", 1500)
        self.assertEqual(self.store.get_budget("2026-11"), 1500)
        self.store.set_budget("2026-11", None)
        self.assertIsNone(self.store.get_budget("2026-11"))
        for value in (-4, 0, "oops", float("inf")):
            with self.assertRaises(ValueError):
                self.store.set_budget("2026-11", value)

    def test_dashboard(self):
        self.add("Cafe", 100, "2026-11-05", "Food")
        self.add("Shop", 150, "2026-11-05", "Shopping")
        self.add("Cafe", 200, "2026-11-06", "Food")
        self.add("Old", 300, "2026-10-04", "Travel")
        self.store.set_budget("2026-11", 200)
        data = self.store.dashboard("2026-11")
        self.assertEqual(data["monthly_total"], 450)
        self.assertEqual(data["all_time_total"], 750)
        self.assertEqual(data["top_category"], "Food")
        self.assertEqual(data["daily_average"], 225)
        self.assertEqual(data["budget_remaining"], -250)

    def test_legacy_database_compatibility(self):
        self.store.close()
        self.db_path.unlink()
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE ExpenseLog (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                       Date TEXT, Payee TEXT, Description TEXT, Category TEXT, Amount REAL, Mode TEXT)""")
            db.execute("INSERT INTO ExpenseLog (Date,Payee,Description,Category,Amount,Mode) VALUES (?,?,?,?,?,?)",
                       ("2025-06-01", "Original", "Old record", "Food", 42, "Cash"))
        self.store = ExpenseStore(self.db_path)
        self.assertEqual(self.store.list_expenses()[0]["Payee"], "Original")
        self.assertIsNone(self.store.get_budget("2025-06"))

    def test_backup_restore(self):
        self.add("Original", 300)
        self.store.set_budget("2026-11", 2000)
        backup = Path(self.temp.name) / "saved.db"
        self.store.backup(backup)
        self.store.clear()
        self.store.set_budget("2026-11", None)
        self.store.restore(backup)
        self.assertEqual(self.store.total(), 300)
        self.assertEqual(self.store.get_budget("2026-11"), 2000)
        with self.assertRaises(ValueError):
            self.store.backup(self.db_path)
        with self.assertRaises(ValueError):
            self.store.restore(self.db_path)

    def test_invalid_backup_rejected(self):
        other = Path(self.temp.name) / "empty.db"
        with sqlite3.connect(other) as db:
            db.execute("CREATE TABLE Random (Name TEXT)")
        self.add("Keep")
        with self.assertRaises(ValueError):
            self.store.restore(other)
        self.assertEqual(len(self.store.list_expenses()), 1)

    def test_export_formats(self):
        self.add("Cafe")
        rows = self.store.list_expenses()
        for suffix, export in (("csv", export_csv), ("xlsx", export_excel), ("pdf", export_pdf)):
            with self.subTest(suffix=suffix):
                out = Path(self.temp.name) / ("report." + suffix)
                export(rows, out)
                self.assertGreater(out.stat().st_size, 30)

    def test_clear(self):
        self.add()
        self.add("Other")
        self.assertEqual(self.store.clear(), 2)
        self.assertEqual(self.store.total(), 0)


if __name__ == "__main__":
    unittest.main()