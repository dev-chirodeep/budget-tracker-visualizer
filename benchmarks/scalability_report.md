# Budget Tracker & Visualizer — Local Scalability Benchmark

**Run date:** 27 November 2026  
**Project:** https://github.com/dev-chirodeep/budget-tracker-visualizer  
**Data:** Synthetic and deterministic (random seed 42); no actual user/customer records  
**Environment:** Linux-6.18.57-x86_64-with-glibc2.41; Python 3.13.5, SQLite 3.46.1, pandas 2.2.3, fpdf2 2.8.5. Virtualized Linux machine; timings will differ on other hardware.

All measurements below are in **milliseconds (ms)** and are medians. Each SQL grouping query was measured 7 times after warm-up, loading all rows 5 times, and completed exports 3 times after warm-up. The dataset was bulk-loaded separately into the same SQLite `ExpenseLog` schema as the desktop application. Tests invoked the project's **actual** `ExpenseStore.summary()`, `ExpenseStore.list_expenses()` and `reporting.export_*()` functions without running the Tkinter interface.

## Timings (ms, lower is faster)

| Operation | 1,000 | 10,000 | 50,000 | 100,000 |
|---|---:|---:|---:|---:|
| SQL Payment method | 0.256 | 2.410 | 13.351 | 31.507 |
| SQL Payee | 0.263 | 2.490 | 15.027 | 36.054 |
| SQL Category | 0.203 | 2.530 | 13.464 | 34.224 |
| SQL Month | 0.510 | 5.935 | 33.102 | 66.844 |
| Fetch all records | 2.642 | 29.109 | 178.830 | 373.300 |
| Export CSV | 4.129 | 28.672 | 158.664 | 283.227 |
| Export Excel | 75.729 | 628.536 | 3,254.643 | 6,846.753 |
| Export PDF | 244.412 | 2,456.880 | Not measured | Not measured |

## Main findings

- On **100,000 synthetic expense records**, each of the 4 grouping queries completed with a median time **under 70 ms** (31.507–66.844 ms).
- On **100,000 records**, exporting to CSV took **283.227 ms**, while exporting to Excel took **6,846.753 ms (about 6.85 seconds)**, both measured as medians of 3 exports.
- At **50,000 rows**, the earlier experiment timed out while executing PDF export; the process exceeded an overall 120-second limit. PDF export was **not measured** in the final 50,000 and 100,000 row runs. PDF scalability is not established and needs optimization.
- Fetching all 100,000 records as Python dictionaries took a median **373.300 ms**. Rendering 100,000 records in a Tkinter table was **not** measured and may be slower.

## What the results do *not* establish

- No real-world users, production traffic, uptime, or percentage performance improvement over a previous version were measured.
- SQL timing measures only aggregation queries, not UI rendering or end-to-end reporting workflow.
- Bulk-loading the synthetic dataset in one transaction does **not** measure normal single-record GUI insertion speed.
- Export timing excludes file chooser interactions and separately timed record retrieval.
- These numbers are environment-specific and may not match performance on Windows.

## Reproduction

Save `budget_tracker_scalability_benchmark.py` beside `main.py`, `storage.py` and `reporting.py`; install the dependencies from `requirements.txt`, then run:

```bash
python budget_tracker_scalability_benchmark.py --rows 1000
python budget_tracker_scalability_benchmark.py --rows 10000
python budget_tracker_scalability_benchmark.py --rows 50000
python budget_tracker_scalability_benchmark.py --rows 100000
```

Output: `budget_scalability_<number>_results.csv`. The script uses a temporary SQLite database and removes it after each test. PDFs are intentionally skipped beyond 10,000 records, because the current exporter was too slow at the 50,000-row scale.

**Potential resume statement (measured, not fabricated):** "Benchmarked SQL aggregation across 100,000 synthetic expense records, achieving median query times below 70 ms in four reporting categories under isolated local test conditions."