# Budget Tracker & Visualizer

I built this desktop application during my Python internship to make everyday expense tracking easier. It uses Tkinter for the interface, SQLite for local storage, and Matplotlib for spending charts. The project has since been updated with expense editing, search, and a separate reporting module.

## What it does

- Add, edit, search and delete expenses with a date, payee, description, category, amount and payment method.
- View total spending and bar charts by category, payee, payment method or month.
- View a category-wise pie chart to understand spending distribution.
- Export expense records to CSV, Excel or PDF.
- Keep records in a local SQLite database without needing an internet connection.

## Getting started

You will need Python 3.10 or later with Tkinter installed.

```bash
git clone https://github.com/dev-chirodeep/budget-tracker-visualizer.git
cd budget-tracker-visualizer
python -m pip install -r requirements.txt
python main.py
```

Fill in the expense details and click **Add expense**. To make changes, select an expense and click **Edit selected** (or double-click its row), update the form, and click **Save changes**. Use the search box to find records by date, payee, description, category or payment method. Charts, totals and exports use all recorded expenses, not just the search results.

## Screenshots

These screenshots show the original internship version. The current interface has additional edit and search controls.

| Dashboard | Pie chart |
| --- | --- |
| ![Expense dashboard](Images/Dashboard.png) | ![Category breakdown](Images/Pie%20Chart.png) |

| Export options | Bar chart |
| --- | --- |
| ![Export options](Images/Export.png) | ![Spending chart](Images/Bar%20chart.png) |

## Project files

| File | Purpose |
| --- | --- |
| `main.py` | Tkinter interface and charts |
| `storage.py` | SQLite queries, expense validation and record management |
| `reporting.py` | CSV, Excel and PDF exports |
| `benchmark.py` | Reporting performance measurements using sample data |
| `tests/test_storage.py` | Automated database and export tests |
| `requirements.txt` | Python dependencies |

## Testing

```bash
python -m unittest discover -s tests -v
```

The tests use temporary databases to check expense management, searching, summaries, input validation and exports. They do not modify existing expense records.

To measure reporting performance on your computer:

```bash
python benchmark.py --rows 1000 --repeats 7
```

The benchmark creates synthetic expenses, measures median SQL query and export times, and saves the results to `benchmark_results.csv`. It does not include GUI rendering or manual interaction. Times vary by machine.

## Local data and limitations

The application opens `expenses.db` in the project folder, creating the table if needed. Back up this file before updating or deleting records. The older `tracker.db` file is not used by the current application; both existing database files are retained to avoid losing data. Do not commit personal expense records to a public repository.

This is a local, single-user application. Login, cloud sync and spending alerts are possible future improvements. PDF exports may shorten long text and replace characters unsupported by the built-in font; CSV and Excel retain the full text.

## License

MIT — see [License.txt](License.txt).
