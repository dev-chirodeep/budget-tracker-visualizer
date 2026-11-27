import tempfile
import unittest
from pathlib import Path

from storage import ExpenseStore
from reporting import export_csv, export_excel, export_pdf


class ExpenseStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"
        self.store = ExpenseStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def add(self, payee="Test Payee", amount=125.5, date="2026-11-27"):
        return self.store.add(date, payee, "Lunch", "Food", amount, "UPI")

    def test_add_read_update_delete(self):
        record_id = self.add()
        self.assertEqual(self.store.get(record_id)["Payee"], "Test Payee")
        self.assertTrue(self.store.update(record_id, "2026-11-28", "Changed", "Dinner",
                                          "Food", 250, "Cash"))
        self.assertEqual(self.store.get(record_id)["Amount"], 250)
        self.assertTrue(self.store.delete(record_id))
        self.assertIsNone(self.store.get(record_id))

    def test_search_and_totals(self):
        self.add("Cafe", 125.5)
        self.add("Pharmacy", 60)
        self.assertEqual(len(self.store.list_expenses("Cafe")), 1)
        self.assertEqual(self.store.total(), 185.5)
        self.assertEqual(self.store.summary("Category"), [("Food", 185.5)])
        self.assertEqual(len(self.store.list_expenses("%")), 0)

    def test_validation_and_safe_grouping(self):
        for amount in (0, -2, "bad", float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.add(amount=amount)
        with self.assertRaises(ValueError):
            self.store.summary("Category; DROP TABLE ExpenseLog")
        with self.assertRaises(ValueError):
            self.store.add("2026-99-99", "A", "B", "C", 1, "Cash")

    def test_existing_schema_compatibility(self):
        self.add()
        self.store.close()
        self.store = ExpenseStore(self.db)
        self.assertEqual(len(self.store.list_expenses()), 1)

    def test_exports(self):
        self.add()
        rows = self.store.list_expenses()
        out = Path(self.tmp.name)
        export_csv(rows, out / "report.csv")
        export_excel(rows, out / "report.xlsx")
        export_pdf(rows, out / "report.pdf")
        for suffix in ("csv", "xlsx", "pdf"):
            self.assertGreater((out / f"report.{suffix}").stat().st_size, 0)
        self.assertIn("Payee", (out / "report.csv").read_text())


if __name__ == "__main__":
    unittest.main()