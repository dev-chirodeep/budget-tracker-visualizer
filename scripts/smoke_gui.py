"""Start the Tkinter window, exercise basic controls, then close it."""
import datetime as dt
from pathlib import Path
import tempfile
from main import BudgetTracker


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = BudgetTracker(Path(directory) / "smoke.db")
        app.update()
        app.store.add(dt.date.today().isoformat(), "Sample", "Coffee", "Food", 95, "UPI")
        app.refresh()
        assert app.table.get_children()
        app.toggle_theme()
        app.update()
        app.toggle_theme()
        app.close()
    print("GUI smoke test passed")


if __name__ == "__main__":
    main()