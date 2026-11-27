"""Capture the live Tkinter UI with a temporary sample database."""
from datetime import date, timedelta
from pathlib import Path
import tempfile
import time

from PIL import Image, ImageGrab
from main import BudgetTracker

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "Images"


def capture(app, filename):
    app.update_idletasks()
    app.update()
    time.sleep(0.25)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    return ImageGrab.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height())).convert("RGB")


def main():
    IMAGES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        app = BudgetTracker(Path(directory) / "sample.db")
        today = date.today()
        examples = (
            ("Groceries", "Weekly shopping", "Food", 780, "UPI", 3),
            ("Metro", "Travel card", "Travel", 180, "Card", 2),
            ("Bookshop", "Study materials", "Shopping", 420, "Cash", 1),
            ("Electricity", "Monthly bill", "Bills", 1320, "Net Banking", 0),
        )
        for payee, note, category, amount, mode, days_ago in examples:
            app.store.add((today - timedelta(days=days_ago)).isoformat(), payee, note,
                          category, amount, mode)
        app.store.set_budget(today.strftime("%Y-%m"), 5000)
        app.refresh()
        frames = []
        light = capture(app, "light")
        light.save(IMAGES / "Dashboard-current.png", optimize=True)
        frames.append(light)
        app.toggle_theme()
        dark = capture(app, "dark")
        dark.save(IMAGES / "Dashboard-dark.png", optimize=True)
        frames.append(dark)
        app.filter_category.set("Food")
        app.refresh()
        frames.append(capture(app, "filtered"))
        app.reset_filters()
        frames.append(capture(app, "reset"))
        app.close()
    # The GIF consists of actual captured windows, not a design mockup.
    frames = [frame.resize((952, 632)).quantize(colors=64) for frame in frames]
    frames[0].save(IMAGES / "demo.gif", save_all=True, append_images=frames[1:],
                   duration=[1800, 1800, 2000, 1800], loop=0, optimize=True)
    print("Captured light/dark screenshots and demo.gif")


if __name__ == "__main__":
    main()