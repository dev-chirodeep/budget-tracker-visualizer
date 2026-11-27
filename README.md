# Budget Tracker & Visualizer

A desktop expense tracker built with **Python, Tkinter, SQLite, pandas, Matplotlib, and FPDF**. It stores expenses locally and supports reporting and export. This project was developed as an internship application and is intended for personal/local use.

## Features

- **Add, edit, search and delete expenses**. Double-click a row or use **Edit selected**, then **Save changes**.
- Store expenses persistently in an SQLite database with a stable primary-key ID.
- Search by payee, description, category, payment mode or date.
- See total spending and generate bar charts by payment method, payee, category or month; category-wise pie chart.
- Export all recorded expenses to **CSV, Excel (.xlsx), or PDF**.
- Validate dates, required text fields and positive finite amounts; use parameterized SQL for user-provided values.
- Confirm deletions before removing entries.

## Screenshots

| Dashboard | Category pie chart |
|---|---|
| ![Dashboard](Images/Dashboard.png) | ![Pie Chart](Images/Pie%20Chart.png) |

| Export choices | Bar chart |
|---|---|
| ![Export](Images/Export.png) | ![Bar Chart](Images/Bar%20chart.png) |

*Screenshots are from an earlier version of the interface; controls and placement may differ in the updated release.*

## Requirements

- Python 3.10 or later with Tkinter (included in most standard Windows Python installations).
- Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The application reads/writes `expenses.db` next to `main.py`. **Back up your existing `expenses.db` before updating.** The original `ExpenseLog` table schema is preserved; existing records are not automatically deleted or migrated. Do not publish personal spending data.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests create temporary databases and exercise expense CRUD, search, validation, aggregation and exports. They do not modify your personal `expenses.db`.

## Performance benchmarking

```bash
python benchmark.py --rows 1000 --repeats 7
```

This generates **synthetic** expenses in a temporary database, times four SQL aggregation queries and three exports, and writes `benchmark_results.csv` locally. Results are machine-dependent and exclude human interaction and GUI rendering. Do not report a percentage improvement unless you measure a comparable baseline separately. The benchmark is independent of your personal data.

## Data and security notes

- `.gitignore` excludes database files and temporary benchmark outputs from future commits. Existing database files committed in the past may remain tracked; remove them separately after backing up and checking for sensitive information.
- SQLite writes are handled through parameterized statements; reporting dimensions use a fixed allowlist.
- There is no authentication, synchronization, cloud backup or multi-user support.
- PDF output uses a standard built-in font; unsupported Unicode symbols may be replaced with `?`.

## Source files

- `main.py`: Tkinter application and charts
- `storage.py`: SQLite data access and validation
- `reporting.py`: CSV, XLSX and PDF exports
- `tests/test_storage.py`: tests
- `benchmark.py`: reproducible synthetic benchmark

## License

See `License.txt`.