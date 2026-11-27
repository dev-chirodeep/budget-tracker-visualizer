"""Budget Tracker & Visualizer desktop application."""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import matplotlib.pyplot as plt

try:
    from tkcalendar import DateEntry
except ImportError:
    # The rest of the application still works if the calendar widget is unavailable.
    class DateEntry(ttk.Entry):
        def __init__(self, master=None, date_pattern=None, **kwargs):
            self.date_value = tk.StringVar(value=dt.date.today().isoformat())
            super().__init__(master, textvariable=self.date_value, **kwargs)

        def get_date(self):
            return dt.date.fromisoformat(self.date_value.get())

        def set_date(self, value):
            if isinstance(value, dt.datetime):
                value = value.date()
            self.date_value.set(value.isoformat() if isinstance(value, dt.date) else str(value))

from reporting import export_csv, export_excel, export_pdf
from storage import ExpenseStore

# Keep normal source runs beside the repository; packaged builds use a user-writable folder.
if getattr(sys, "frozen", False):
    ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "BudgetTracker"
    ROOT.mkdir(parents=True, exist_ok=True)
else:
    ROOT = Path(__file__).resolve().parent
CATEGORIES = ("General", "Food", "Travel", "Bills", "Health", "Shopping", "Other")
MODES = ("Cash", "Card", "UPI", "Net Banking", "Other")

PALETTES = {
    "light": {"bg": "#f5f7fa", "panel": "#ffffff", "ink": "#1e293b", "muted": "#64748b", "accent": "#2563eb", "border": "#dbe2ec"},
    "dark": {"bg": "#131923", "panel": "#202a38", "ink": "#eef2f7", "muted": "#b6c4d3", "accent": "#60a5fa", "border": "#354457"},
}


class BudgetTracker(tk.Tk):
    def __init__(self, database_path: str | Path | None = None) -> None:
        super().__init__()
        self.store = ExpenseStore(database_path or ROOT / "expenses.db")
        self.editing_id: int | None = None
        self.theme_name = "light"
        self.month = dt.date.today().strftime("%Y-%m")
        self.title("Budget Tracker & Visualizer")
        self.geometry("1190x790")
        self.minsize(980, 740)
        self._build_ui()
        self._apply_theme()
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build_ui(self) -> None:
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.payee = tk.StringVar()
        self.description = tk.StringVar()
        self.category = tk.StringVar(value=CATEGORIES[0])
        self.amount = tk.StringVar()
        self.mode = tk.StringVar(value=MODES[0])
        self.search_text = tk.StringVar()
        self.date_from = tk.StringVar()
        self.date_to = tk.StringVar()
        self.filter_category = tk.StringVar(value="All")
        self.filter_mode = tk.StringVar(value="All")
        self.min_amount = tk.StringVar()
        self.max_amount = tk.StringVar()
        self.report_group = tk.StringVar(value="Category")

        header = ttk.Frame(self, style="App.TFrame", padding=(20, 16))
        header.pack(fill="x")
        ttk.Label(header, text="Budget Tracker", style="Heading.TLabel").pack(side="left")
        ttk.Label(header, text="  /  Expenses and reports", style="Subheading.TLabel").pack(side="left", pady=7)
        ttk.Button(header, text="Change theme", command=self.toggle_theme).pack(side="right", padx=5)
        ttk.Button(header, text="Restore backup", command=self.restore_backup).pack(side="right", padx=5)
        ttk.Button(header, text="Back up data", command=self.backup_data).pack(side="right", padx=5)

        cards = ttk.Frame(self, style="App.TFrame", padding=(20, 0, 20, 10))
        cards.pack(fill="x")
        self.card_values = {}
        for idx, (name, label) in enumerate((
            ("month", "THIS MONTH"), ("all", "ALL-TIME SPENDING"),
            ("top", "TOP CATEGORY"), ("average", "AVERAGE PER ACTIVE DAY"),
        )):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 7, 0))
            cards.columnconfigure(idx, weight=1)
            ttk.Label(card, text=label, style="Caption.TLabel").pack(anchor="w")
            value = ttk.Label(card, text="—", style="Number.TLabel")
            value.pack(anchor="w", pady=(7, 0))
            self.card_values[name] = value

        budget_bar = ttk.Frame(self, style="App.TFrame", padding=(20, 3, 20, 9))
        budget_bar.pack(fill="x")
        self.budget_label = ttk.Label(budget_bar, text="Monthly budget: not set", style="Subheading.TLabel")
        self.budget_label.pack(side="left")
        ttk.Button(budget_bar, text="Set monthly budget", command=self.set_budget).pack(side="right")

        form = ttk.LabelFrame(self, text=" Expense details ", padding=(12, 10))
        form.pack(fill="x", padx=20, pady=(2, 9))
        for idx, label in enumerate(("Date", "Payee", "Description", "Category", "Amount (INR)", "Payment method")):
            ttk.Label(form, text=label).grid(row=0, column=idx, sticky="w", padx=4)
            form.columnconfigure(idx, weight=1)
        self.date_input = DateEntry(form, date_pattern="yyyy-mm-dd", width=12)
        self.date_input.grid(row=1, column=0, padx=4, sticky="ew")
        ttk.Entry(form, textvariable=self.payee).grid(row=1, column=1, padx=4, sticky="ew")
        ttk.Entry(form, textvariable=self.description).grid(row=1, column=2, padx=4, sticky="ew")
        ttk.Combobox(form, textvariable=self.category, values=CATEGORIES, state="readonly").grid(row=1, column=3, padx=4, sticky="ew")
        ttk.Entry(form, textvariable=self.amount).grid(row=1, column=4, padx=4, sticky="ew")
        ttk.Combobox(form, textvariable=self.mode, values=MODES, state="readonly").grid(row=1, column=5, padx=4, sticky="ew")
        actions = ttk.Frame(form)
        actions.grid(row=2, column=0, columnspan=6, sticky="w", pady=(11, 0))
        self.save_button = ttk.Button(actions, text="Add expense", command=self.save)
        self.save_button.pack(side="left", padx=(0, 6))
        for label, handler in (("Edit selected", self.load_selected), ("Clear form", self.reset_form),
                               ("Delete selected", self.delete_selected), ("Delete all", self.delete_all)):
            ttk.Button(actions, text=label, command=handler).pack(side="left", padx=4)

        filters = ttk.LabelFrame(self, text=" Find expenses ", padding=(12, 8))
        filters.pack(fill="x", padx=20, pady=3)
        configs = (
            ("Search", self.search_text, 23), ("From (YYYY-MM-DD)", self.date_from, 15),
            ("To (YYYY-MM-DD)", self.date_to, 15),
            ("Category", self.filter_category, 11), ("Payment", self.filter_mode, 11),
            ("Min INR", self.min_amount, 10), ("Max INR", self.max_amount, 10),
        )
        for idx, (label, var, width) in enumerate(configs):
            ttk.Label(filters, text=label).grid(row=0, column=idx, sticky="w", padx=3)
            if label == "Category":
                w = ttk.Combobox(filters, textvariable=var, values=("All", *CATEGORIES), width=width, state="readonly")
            elif label == "Payment":
                w = ttk.Combobox(filters, textvariable=var, values=("All", *MODES), width=width, state="readonly")
            else:
                w = ttk.Entry(filters, textvariable=var, width=width)
                w.bind("<Return>", lambda _event: self.refresh())
            w.grid(row=1, column=idx, sticky="ew", padx=3)
            filters.columnconfigure(idx, weight=1)
        filter_actions = ttk.Frame(filters)
        filter_actions.grid(row=2, column=0, columnspan=7, sticky="w", pady=(7, 0))
        ttk.Button(filter_actions, text="Apply filters", command=self.refresh).pack(side="left")
        ttk.Button(filter_actions, text="Reset filters", command=self.reset_filters).pack(side="left", padx=8)
        self.row_label = ttk.Label(filter_actions, text="0 records")
        self.row_label.pack(side="left", padx=10)

        table_frame = ttk.Frame(self, style="App.TFrame", padding=(20, 8, 20, 4))
        table_frame.pack(fill="both", expand=True)
        cols = ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=6)
        for column in cols:
            self.table.heading(column, text=column)
            self.table.column(column, anchor="w", width=205 if column == "Description" else 115, minwidth=65)
        ys = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        xs = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.table.pack(fill="both", expand=True)
        self.table.bind("<Double-1>", lambda _event: self.load_selected())

        footer = ttk.Frame(self, style="App.TFrame", padding=(20, 7, 20, 15))
        footer.pack(fill="x")
        ttk.Label(footer, text="Spending by").pack(side="left")
        ttk.Combobox(footer, textvariable=self.report_group, values=("Category", "Month", "Payee", "Payment method"),
                     state="readonly", width=15).pack(side="left", padx=(5, 10))
        for label, fn in (("Bar chart", self.bar_chart), ("Pie chart", self.pie_chart),
                          ("Export CSV", lambda: self.export("csv")),
                          ("Export Excel", lambda: self.export("xlsx")),
                          ("Export PDF", lambda: self.export("pdf"))):
            ttk.Button(footer, text=label, command=fn).pack(side="left", padx=3)
        ttk.Label(footer, text="Reports include all records", style="Subheading.TLabel").pack(side="right")

    def _apply_theme(self) -> None:
        p = PALETTES[self.theme_name]
        self.configure(bg=p["bg"])
        self.style.configure("App.TFrame", background=p["bg"])
        self.style.configure("TFrame", background=p["panel"])
        self.style.configure("TLabelframe", background=p["panel"], bordercolor=p["border"])
        self.style.configure("TLabelframe.Label", background=p["panel"], foreground=p["ink"])
        self.style.configure("TLabel", background=p["panel"], foreground=p["ink"])
        self.style.configure("Heading.TLabel", background=p["bg"], foreground=p["ink"], font=("Segoe UI", 20, "bold"))
        self.style.configure("Subheading.TLabel", background=p["bg"], foreground=p["muted"], font=("Segoe UI", 9))
        self.style.configure("Card.TFrame", background=p["panel"], relief="flat")
        self.style.configure("Caption.TLabel", background=p["panel"], foreground=p["muted"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Number.TLabel", background=p["panel"], foreground=p["ink"], font=("Segoe UI", 18, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 9), padding=(9, 6), background=p["panel"], foreground=p["ink"], bordercolor=p["border"])
        self.style.map("TButton", background=[("active", p["border"])])
        self.style.configure("TEntry", fieldbackground=p["panel"], foreground=p["ink"], insertcolor=p["ink"])
        self.style.configure("TCombobox", fieldbackground=p["panel"], foreground=p["ink"])
        self.style.configure("Treeview", background=p["panel"], fieldbackground=p["panel"], foreground=p["ink"], rowheight=27)
        self.style.configure("Treeview.Heading", background=p["border"], foreground=p["ink"], font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", p["accent"])], foreground=[("selected", "#ffffff")])

    def toggle_theme(self) -> None:
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self._apply_theme()

    def _form_values(self) -> tuple:
        return (self.date_input.get_date().isoformat(), self.payee.get(), self.description.get(),
                self.category.get(), self.amount.get(), self.mode.get())

    def save(self) -> None:
        try:
            if self.editing_id is None:
                self.store.add(*self._form_values())
            elif not self.store.update(self.editing_id, *self._form_values()):
                raise ValueError("This expense no longer exists.")
            self.reset_form()
            self.refresh()
        except (ValueError, OverflowError) as exc:
            messagebox.showwarning("Check the details", str(exc))
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc))

    def _selected_id(self) -> int | None:
        selected = self.table.selection()
        if not selected:
            messagebox.showinfo("Select an expense", "Choose a row first.")
            return None
        return int(self.table.item(selected[0], "values")[0])

    def load_selected(self) -> None:
        record_id = self._selected_id()
        if record_id is None:
            return
        record = self.store.get(record_id)
        if record is None:
            self.refresh()
            return
        self.editing_id = record_id
        try:
            self.date_input.set_date(dt.date.fromisoformat(record["Date"]))
        except (TypeError, ValueError):
            self.date_input.set_date(dt.date.today())
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
        self.mode.set(MODES[0])
        self.save_button.configure(text="Add expense")

    def refresh(self) -> None:
        try:
            records = self.store.list_expenses(
                self.search_text.get(), date_from=self.date_from.get(), date_to=self.date_to.get(),
                category=self.filter_category.get(), mode=self.filter_mode.get(),
                min_amount=self.min_amount.get(), max_amount=self.max_amount.get())
        except ValueError as exc:
            messagebox.showwarning("Check the filters", str(exc))
            return
        self.table.delete(*self.table.get_children())
        for item in records:
            fields = ("ID", "Date", "Payee", "Description", "Category", "Amount", "Mode")
            values = tuple(f"{item[col]:,.2f}" if col == "Amount" else item[col] for col in fields)
            self.table.insert("", "end", values=values)
        self.row_label.configure(text=f"{len(records)} records shown")
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        stats = self.store.dashboard(self.month)
        self.card_values["month"].configure(text=f"INR {stats['monthly_total']:,.2f}")
        self.card_values["all"].configure(text=f"INR {stats['all_time_total']:,.2f}")
        self.card_values["top"].configure(text=stats["top_category"])
        self.card_values["average"].configure(text=f"INR {stats['daily_average']:,.2f}")
        budget = stats["budget"]
        if budget is None:
            label = f"Budget for {self.month}: not set"
        else:
            remaining = stats["budget_remaining"]
            label = (f"Budget for {self.month}: INR {budget:,.2f}  |  "
                     f"{'Over budget by' if remaining < 0 else 'Remaining'} INR {abs(remaining):,.2f}")
        self.budget_label.configure(text=label)
        if budget and stats["monthly_total"] > budget:
            self.budget_label.configure(foreground="#dc2626")
        else:
            self.budget_label.configure(foreground=PALETTES[self.theme_name]["muted"])

    def reset_filters(self) -> None:
        for value in (self.search_text, self.date_from, self.date_to, self.min_amount, self.max_amount):
            value.set("")
        self.filter_category.set("All")
        self.filter_mode.set("All")
        self.refresh()

    def set_budget(self) -> None:
        existing = self.store.get_budget(self.month)
        value = simpledialog.askstring("Monthly budget", f"Set budget for {self.month} (INR).\nLeave empty to remove it:",
                                       initialvalue=str(existing or ""), parent=self)
        if value is None:
            return
        try:
            self.store.set_budget(self.month, value.strip() or None)
            self.refresh_dashboard()
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showwarning("Budget not saved", str(exc))

    def delete_selected(self) -> None:
        record_id = self._selected_id()
        if record_id is not None and messagebox.askyesno("Delete expense", "Delete this expense?", parent=self):
            self.store.delete(record_id)
            if self.editing_id == record_id:
                self.reset_form()
            self.refresh()

    def delete_all(self) -> None:
        if messagebox.askyesno("Delete all expenses", "Delete all expense records? This cannot be undone.\nConsider backing up first.", parent=self):
            self.store.clear()
            self.reset_form()
            self.refresh()

    def backup_data(self) -> None:
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".db", filetypes=[("SQLite backup", "*.db")])
        if not path:
            return
        try:
            self.store.backup(path)
            messagebox.showinfo("Backup saved", f"Saved a copy to:\n{path}", parent=self)
        except (OSError, sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Backup failed", str(exc), parent=self)

    def restore_backup(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("SQLite databases", "*.db *.sqlite *.sqlite3")])
        if not path:
            return
        if not messagebox.askyesno("Restore backup", "Restoring replaces all current records and budgets.\nBack up your current data first. Continue?", parent=self):
            return
        try:
            self.store.restore(path)
            self.reset_form()
            self.reset_filters()
            messagebox.showinfo("Backup restored", "Your expenses have been restored.", parent=self)
        except (OSError, sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Restore failed", str(exc), parent=self)

    def bar_chart(self) -> None:
        self._draw_chart(self.report_group.get(), pie=False)

    def pie_chart(self) -> None:
        self._draw_chart("Category", pie=True)

    def _draw_chart(self, group: str, *, pie: bool) -> None:
        data = self.store.summary(group)
        if not data:
            messagebox.showinfo("No expenses", "Add expenses to see a chart.", parent=self)
            return
        names, amounts = zip(*data)
        fig, ax = plt.subplots(figsize=(9, 5))
        if pie:
            ax.pie(amounts, labels=names, autopct="%1.1f%%")
        else:
            ax.bar(names, amounts)
            ax.set_ylabel("Amount (INR)")
            ax.tick_params(axis="x", labelrotation=35)
        ax.set_title(f"Expenses by {group.lower()}")
        fig.tight_layout()
        plt.show()

    def export(self, kind: str) -> None:
        rows = self.store.list_expenses()  # Exports cover all records, not just filtered rows.
        if not rows:
            messagebox.showinfo("No expenses", "Add expenses before exporting.", parent=self)
            return
        extensions = {"csv": ("CSV", "*.csv"), "xlsx": ("Excel", "*.xlsx"), "pdf": ("PDF", "*.pdf")}
        path = filedialog.asksaveasfilename(parent=self, defaultextension=f".{kind}", filetypes=[extensions[kind]])
        if not path:
            return
        try:
            {"csv": export_csv, "xlsx": export_excel, "pdf": export_pdf}[kind](rows, path)
            messagebox.showinfo("Report exported", f"Saved to:\n{path}", parent=self)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("Export failed", str(exc), parent=self)

    def close(self) -> None:
        self.store.close()
        self.destroy()


def main() -> None:
    BudgetTracker().mainloop()


if __name__ == "__main__":
    main()