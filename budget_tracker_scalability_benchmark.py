"""Scalability benchmark for the actual Budget Tracker SQLite queries and exports.
Uses deterministic synthetic expenses in temporary SQLite databases, never personal data.
Usage: python budget_tracker_scalability_benchmark.py --rows 10000
"""
import argparse
import csv
import json
import platform
import random
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if not (PROJECT_DIR / "storage.py").exists():
    PROJECT_DIR = PROJECT_DIR / "budget_tracker_v2"  # convenient for the downloaded standalone script
sys.path.insert(0, str(PROJECT_DIR))
from storage import ExpenseStore
from reporting import export_csv, export_excel, export_pdf

OUTPUT_DIR = Path(__file__).resolve().parent


def measure(fn, repeats):
    fn()  # warm up before timing
    durations = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        fn()
        durations.append((time.perf_counter_ns() - start) / 1_000_000)
    return round(statistics.median(durations), 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, required=True)
    args = parser.parse_args()
    n = args.rows
    if n <= 0 or n > 100000:
        parser.error('--rows must be between 1 and 100000')
    rng = random.Random(42)
    samples = [(f'2026-{i % 12 + 1:02d}-{i % 28 + 1:02d}', f'Payee {i % 20}',
                'Sample purchase', 'Food' if i % 2 else 'Travel',
                rng.randint(100,5000)/10, 'UPI' if i % 2 else 'Cash') for i in range(n)]
    rows = []
    with tempfile.TemporaryDirectory(prefix='budget_scalability_') as folder:
        tmp = Path(folder)
        db = ExpenseStore(tmp / 'sample.db')
        try:
            start = time.perf_counter_ns()
            # Batch load is test setup. This is not timing Tkinter Add Expense.
            with db.conn:
                db.conn.executemany('''INSERT INTO ExpenseLog
                   (Date,Payee,Description,Category,Amount,Mode) VALUES (?,?,?,?,?,?)''', samples)
            seed_ms = round((time.perf_counter_ns()-start)/1000000,3)
            assert db.conn.execute('SELECT COUNT(*) FROM ExpenseLog').fetchone()[0] == n
            rows.append({'records':n,'operation':'Synthetic data setup (bulk insert)','median_ms':seed_ms,'repeats':1,'notes':'single transaction; not GUI insert'})
            print(f'{n:,} records, bulk setup {seed_ms:,.3f} ms',flush=True)
            for group in ('Payment method', 'Payee','Category','Month'):
                ms=measure(lambda g=group: db.summary(g),7)
                print(f'  SQL {group:16s} {ms:,.3f} ms',flush=True)
                rows.append({'records':n,'operation':'SQL '+group,'median_ms':ms,'repeats':7,'notes':'query only; excludes GUI'})
            ms=measure(lambda:db.list_expenses(),5)
            print(f'  Fetch all records  {ms:,.3f} ms',flush=True)
            rows.append({'records':n,'operation':'Fetch all records','median_ms':ms,'repeats':5,'notes':'SELECT and Python dict conversion; excludes GUI'})
            records=db.list_expenses()
            assert len(records)==n
            for label,extension,fn in (('CSV','csv',export_csv),('Excel','xlsx',export_excel),('PDF','pdf',export_pdf)):
                if label == 'PDF' and n > 10000:
                    print(f'  Export PDF            not measured (over 10,000 rows; slow)', flush=True)
                    rows.append({'records':n,'operation':'Export PDF','median_ms':'','repeats':0,'notes':'not measured; large PDF is a known performance limitation'})
                    continue
                path=tmp / f'benchmark.{extension}'
                ms=measure(lambda f=fn,p=path:f(records,p),3)
                size=path.stat().st_size
                print(f'  Export {label:15s} {ms:,.3f} ms, {size:,} bytes',flush=True)
                rows.append({'records':n,'operation':'Export '+label,'median_ms':ms,'repeats':3,'notes':f'file size {size} bytes; all {n} rows'})
            rows.append({'records':n,'operation':'SQLite file size','median_ms':'','repeats':0,'notes':f'{(tmp / "sample.db").stat().st_size} bytes'})
        finally:
            db.close()
    destination=OUTPUT_DIR / f'budget_scalability_{n}_results.csv'
    with destination.open('w',newline='',encoding='utf-8') as out:
        w=csv.DictWriter(out,fieldnames=['records','operation','median_ms','repeats','notes'])
        w.writeheader();w.writerows(rows)
    print('Saved',destination,flush=True)


if __name__=='__main__':main()