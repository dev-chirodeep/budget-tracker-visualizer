"""Measure SQL report and export timings using synthetic expenses."""
import argparse
import csv
import random
import statistics
import tempfile
import time
from pathlib import Path

from storage import ExpenseStore
from reporting import export_csv, export_excel, export_pdf


def timed(action, repeats):
    values = []
    for _ in range(repeats):
        start = time.perf_counter()
        action()
        values.append((time.perf_counter() - start) * 1000)
    return round(statistics.median(values), 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if args.rows <= 0 or args.repeats <= 0:
        parser.error("--rows and --repeats must be positive")
    rng = random.Random(42)
    with tempfile.TemporaryDirectory() as directory:
        db = ExpenseStore(Path(directory) / "benchmark.db")
        try:
            for i in range(args.rows):
                db.add(f"2026-{i % 12 + 1:02d}-{i % 28 + 1:02d}",
                       f"Payee {i % 20}", "Sample", "Food" if i % 2 else "Travel",
                       rng.randint(100, 5000) / 10, "UPI" if i % 2 else "Cash")
            rows = db.list_expenses()
            results = {}
            for group in ("Payment method", "Payee", "Category", "Month"):
                results[f"SQL {group}"] = timed(lambda g=group: db.summary(g), args.repeats)
            exports = (("CSV", "csv", export_csv),
                       ("Excel", "xlsx", export_excel),
                       ("PDF", "pdf", export_pdf))
            for label, extension, exporter in exports:
                path = Path(directory) / f"bench.{extension}"
                results[f"Export {label}"] = timed(
                    lambda fn=exporter, output=path: fn(rows, output), args.repeats)
            print(f"Synthetic rows: {args.rows}; repeats: {args.repeats}; median milliseconds")
            for name, ms in results.items():
                print(f"{name}: {ms} ms")
            with (Path.cwd() / "benchmark_results.csv").open("w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(("operation", "median_ms", "synthetic_rows", "repeats"))
                for name, ms in results.items():
                    writer.writerow((name, ms, args.rows, args.repeats))
        finally:
            db.close()


if __name__ == "__main__":
    main()