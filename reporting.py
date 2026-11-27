"""Export expenses to CSV, Excel and PDF."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from fpdf import FPDF
from storage import FIELDS


def _frame(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records, columns=FIELDS)


def export_csv(records: list[dict], filename: str | Path) -> None:
    _frame(records).to_csv(filename, index=False)


def export_excel(records: list[dict], filename: str | Path) -> None:
    _frame(records).to_excel(filename, index=False)


def _pdf_text(value: object) -> str:
    # Helvetica cannot display every Unicode character.
    return str(value).encode("latin-1", errors="replace").decode("latin-1")


def export_pdf(records: list[dict], filename: str | Path) -> None:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 11, "Budget Tracker - Expense Report", new_x="LMARGIN", new_y="NEXT")
    widths = (13, 25, 38, 68, 35, 30, 45)

    def header() -> None:
        pdf.set_font("Helvetica", "B", 9)
        for name, width in zip(FIELDS, widths):
            pdf.cell(width, 8, name, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", size=8)

    header()
    for record in records:
        if pdf.get_y() > 184:
            pdf.add_page()
            header()
        for field, width in zip(FIELDS, widths):
            value = _pdf_text(record.get(field, ""))
            if field == "Amount":
                value = f"{float(record.get(field, 0)):,.2f}"
            if pdf.get_string_width(value) > width - 3:
                while value and pdf.get_string_width(value + "...") > width - 3:
                    value = value[:-1]
                value += "..."
            pdf.cell(width, 7, value, border=1)
        pdf.ln()
    pdf.output(str(filename))