"""Tkinter interface for the expense tracker."""
from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from tkcalendar import DateEntry

from reporting import export_csv, export_excel, export_pdf
from storage import ExpenseStore

PROJECT_DIR = Path(__file__).resolve().parent
DB_FILE_PATH = PROJECT_DIR / "expenses.db"
CATEGORIES = ("General", "Food", "Travel", "Bills", "Health", "Shopping", "Other")
PAYMENT_MODES = ("Cash", "Card", "UPI", "Net Banking", "Other")


class BudgetTracker(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.store = ExpenseStore(DB_FILE_PATH)
        self.editing_id: int | None = None
        self.title("Budget Tracker & Visualizer")
        self.geometry("1120x720")
        self.minsize(950, 580)
        self.configure(bg="#FAF9F6")
        self._build_ui()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        tk.Label(self, text="Budget Tracker & Visualizer", font=("Arial", 21, "bold"),
                 bg="#3F51B5", fg="white", pady=12).pack(fill="x")
        self.payee = tk.StringVar()
        self.description = tk.StringVar()
        self.category = tk.StringVar(value=CATEGORIES[0])
        self.amount = tk.StringVar()
        self.mode = tk.StringVar(value=PAYMENT_MODES[0])
        self.search_text = tk.StringVar()
        self.report_group = tk.StringVar(value="Payment method")

        form = ttk.LabelFrame(self, text="Expense details", padding=10)
        form.pack(fill="x", padx=12, pady=9)
        labels = ("Date", "Payee", "Description", "Category", "Amount (INR)", "Payment mode")
        for index, label in enumerate(labels):
            ttk.Label(form, text=label).grid(row=0, column=index, sticky="w", padx=4)
        self.date_input = DateEntry(form, date_pattern="yyyy-mm-dd", width=12)
        self.date_input.grid(row=1, column=0, padx=4, sticky="ew")
        for i, variable in enumerate((self.payee, self.description), start=1):
            ttk.Entry(form, textvariable=variable).grid(row=1, column=i, padx=4, sticky="ew")
        ttk.Combobox(form, textvariable=self.category, values=CATEGORIES, state="readonly").grid(
            row=1, column=3, padx=4, sticky="ew")
        ttk.Entry(form, textvariable=self.amount).grid(row=1, column=4, padx=4, sticky="ew")
        ttk.Combobox(form, textvariable=self.mode, values=PAYMENT_MODES, state="readonly").grid(
            row=1, column=5, padx=4, sticky="ew")
        for i in range(6):
            form.columnconfigure(i, weight=1)

        actions = ttk.Frame(form)
        actions.grid(row=2, column=0, columnspan=6, sticky="w", pady=(10, 0))
        self.save_button = ttk.Button(actions, text="Add expense", command=self.save)
        self.save_button.pack(side="left", padx=(0, 7))
        ttk.Button(actions, text="Edit selected", command=self.load_selected).pack(side="left", padx=7)
        ttk.Button(actions, text="Clear form", command=self.reset_form).pack(side="left", padx=7)
        ttk.Button(actions, text="Delete selected", command=self.delete_selected).pack(side="left", padx=7)
        ttk.Button(actions, text="Delete all", command=self.delete_all).pack(side="left", padx=7)

        search_area = ttk.Frame(self, padding=(12, 1))
        search_area.pack(fill="x")
        ttk.Label(search_area, text="Search expenses:").pack(side="left")
        search_entry = ttk.Entry(search_area, textvariable=self.search_text, width=37)
        search_entry.pack(side="left", padx=8)
        search_entry.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(search_area, text="Search", command=self.refresh).pack(side="left")
        ttk.Button(search_area, text="Show all", command=self.clear_search).pack(side="left", padx=8)
        self.total_label = ttk.Label(search_area, text="")
        self.total_label.pack(side="right")

        table_frame = ttk.Frame(self, padding=12)
        table_frame.pack(fill="both", expand=True)
        columns = ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=90 if column != "Description" else 220, anchor="w")
        bar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(xscrollcommand=horizontal.set)
        horizontal.pack(side="bottom", fill="x")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", lambda _e: self.load_selected())

        reports = ttk.Frame(self, padding=(12, 4, 12, 12))
        reports.pack(fill="x")
        ttk.Label(reports, text="Group by:").pack(side="left")
        ttk.Combobox(reports, textvariable=self.report_group,
                     values=("Payment method", "Payee", "Category", "Month"),
                     width=18, state="readonly").pack(side="left", padx=6)
        ttk.Button(reports, text="Bar chart", command=self.bar_chart).pack(side="left", padx=5)
        ttk.Button(reports, text="Pie chart (category)", command=self.pie_chart).pack(side="left", padx=5)
        ttk.Button(reports, text="Export CSV", command=lambda: self.export("csv")).pack(side="left", padx=5)
        ttk.Button(reports, text="Export Excel", command=lambda: self.export("xlsx")).pack(side="left", padx=5)
        ttk.Button(reports, text="Export PDF", command=lambda: self.export("pdf")).pack(side="left", padx=5)

    def _form_values(self) -> tuple:
        return (self.date_input.get_date().isoformat(), self.payee.get(),
                self.description.get(), self.category.get(), self.amount.get(), self.mode.get())

    def save(self) -> None:
        try:
            if self.editing_id is None:
                self.store.add(*self._form_values())
            elif not self.store.update(self.editing_id, *self._form_values()):
                raise ValueError("This expense no longer exists.")
            self.reset_form()
            self.refresh()
        except (ValueError, OverflowError) as exc:
            messagebox.showwarning("Check expense details", str(exc))
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc))

    def _selected_id(self) -> int | None:
        selection = self.table.selection()
        if not selection:
            messagebox.showwarning("Select an expense", "Choose a row first.")
            return None
        return int(self.table.item(selection[0], "values")[0])

    def load_selected(self) -> None:
        record_id = self._selected_id()
        if record_id is None:
            return
        record = self.store.get(record_id)
        if record is None:
            self.refresh()
            return
        self.editing_id = record_id
        self.date_input.set_date(dt.date.fromisoformat(record["Date"]))
        self.payee.set(record["Payee"])
        self.description.set(record["Description"])
        self.category.set(record["Category"])
        self.amount.set(str(record["Amount"]))
        self.mode.set(record["Mode"])
        self.save_button.configure(text="Save changes")

    def reset_form(self) -> None:
        self.editing_id = None
        self.date_input.set_date(dt.date.today())
        self.payee.set("")
        self.description.set("")
        self.category.set(CATEGORIES[0])
        self.amount.set("")
        self.mode.set(PAYMENT_MODES[0])
        self.save_button.configure(text="Add expense")

    def refresh(self) -> None:
        self.table.delete(*self.table.get_children())
        for record in self.store.list_expenses(self.search_text.get()):
            values = tuple(f"{record[c]:.2f}" if c == "Amount" else record[c]
                           for c in ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode"))
            self.table.insert("", "end", values=values)
        self.total_label.configure(text=f"Total spending (all records): INR {self.store.total():,.2f}")

    def clear_search(self) -> None:
        self.search_text.set("")
        self.refresh()

    def delete_selected(self) -> None:
        record_id = self._selected_id()
        if record_id is not None and messagebox.askyesno("Confirm deletion", "Delete this expense?"):
            self.store.delete(record_id)
            if self.editing_id == record_id:
                self.reset_form()
            self.refresh()

    def delete_all(self) -> None:
        if messagebox.askyesno("Delete all expenses", "Delete ALL records permanently? This cannot be undone."):
            self.store.clear()
            self.reset_form()
            self.refresh()

    def bar_chart(self) -> None:
        self._draw_chart(self.report_group.get(), pie=False)

    def pie_chart(self) -> None:
        self._draw_chart("Category", pie=True)

    def _draw_chart(self, group: str, *, pie: bool) -> None:
        data = self.store.summary(group)
        if not data:
            messagebox.showinfo("No data", "Add expenses to generate a chart.")
            return
        labels, amounts = zip(*data)
        fig, ax = plt.subplots(figsize=(9, 5))
        if pie:
            ax.pie(amounts, labels=labels, autopct="%1.1f%%")
        else:
            ax.bar(labels, amounts)
            ax.set_ylabel("Amount (INR)")
            ax.tick_params(axis="x", labelrotation=35)
        ax.set_title(f"Expenses by {group}")
        fig.tight_layout()
        plt.show()

    def export(self, format_name: str) -> None:
        records = self.store.list_expenses()  # Export all records, even when search is active.
        if not records:
            messagebox.showinfo("No data", "Add expenses before exporting.")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{format_name}",
            filetypes={"csv": [("CSV", "*.csv")], "xlsx": [("Excel", "*.xlsx")],
                       "pdf": [("PDF", "*.pdf")]}[format_name])
        if not filename:
            return
        try:
            {"csv": export_csv, "xlsx": export_excel, "pdf": export_pdf}[format_name](records, filename)
            messagebox.showinfo("Export complete", f"Saved report to:\n{filename}")
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Export failed", str(exc))

    def _on_close(self) -> None:
        self.store.close()
        self.destroy()


def main() -> None:
    BudgetTracker().mainloop()


if __name__ == "__main__":
    main()
