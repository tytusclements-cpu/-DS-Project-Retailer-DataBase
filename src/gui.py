# gui.py
# Graphical interface for the Retailer Database System.
#
# Run with:  python src/gui.py
# The connection uses the same RETAIL_DB_* settings as the console app; if it
# cannot connect, a sign-in window asks for the details.

import queue
import sys
import threading
import time
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

try:
    import oracledb
except ImportError:                                     # pragma: no cover
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Missing package",
        "The 'oracledb' package is not installed.\n\n"
        "Install it with:\n    python -m pip install oracledb"
    )
    sys.exit(1)

import database
from cli_utils import UserError, describe_db_error
from database import DatabaseUnavailableError
from gui_catalog import (
    CustomersPage, ProductsPage, StoresPage, VendorsPage,
)
from gui_dialogs import ConnectDialog
from gui_insights import DashboardPage, ReportsPage
from gui_operations import InventoryPage, OrdersPage, SalesPage
from gui_theme import C, apply_theme, font, px

APP_NAME = "Retailer Database"

# (section, [(label, page class)])
NAVIGATION = [
    ("OVERVIEW", [("Dashboard", DashboardPage)]),
    ("CATALOG", [("Products", ProductsPage), ("Stores", StoresPage),
                 ("Customers", CustomersPage), ("Vendors", VendorsPage)]),
    ("OPERATIONS", [("Inventory", InventoryPage), ("Sales", SalesPage),
                    ("Orders", OrdersPage)]),
    ("INSIGHTS", [("Reports", ReportsPage)]),
]

TOAST_COLOURS = {
    "success": C["success"],
    "warning": C["warning"],
    "error": C["danger"],
}


# --------------------------------------------------
# CONNECTION
# --------------------------------------------------

def current_settings():
    return {
        "user": database.DB_USER,
        "password": database.DB_PASSWORD,
        "host": database.DB_HOST,
        "port": database.DB_PORT,
        "service": database.DB_SERVICE,
    }


def apply_settings(settings):
    """Point database.py at the chosen database (read on every connect)."""

    database.DB_USER = settings["user"]
    database.DB_PASSWORD = settings["password"]
    database.DB_HOST = settings["host"]
    database.DB_PORT = int(settings["port"])
    database.DB_SERVICE = settings["service"]


def try_connect(settings):
    """Open and close a connection; raises if it cannot be made."""

    connection = oracledb.connect(
        user=settings["user"], password=settings["password"],
        dsn=f"{settings['host']}:{settings['port']}/{settings['service']}"
    )
    connection.close()


# --------------------------------------------------
# SIDEBAR ITEM
# --------------------------------------------------

class NavItem(tk.Frame):
    def __init__(self, parent, text, command):
        super().__init__(parent, bg=C["sidebar"], cursor="hand2")

        self._active = False

        self.bar = tk.Frame(self, bg=C["sidebar"], width=4)
        self.bar.pack(side="left", fill="y")

        self.label = tk.Label(
            self, text=text, bg=C["sidebar"], fg=C["sidebar_text"],
            font=font(10), anchor="w", padx=16, pady=9
        )
        self.label.pack(side="left", fill="x", expand=True)

        for widget in (self, self.label):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", lambda _e: self._paint(hover=True))
            widget.bind("<Leave>", lambda _e: self._paint(hover=False))

    def set_active(self, active):
        self._active = active
        self._paint()

    def _paint(self, hover=False):
        background = (C["sidebar_hover"] if self._active or hover
                      else C["sidebar"])

        self.configure(bg=background)
        self.label.configure(
            bg=background,
            fg="#ffffff" if self._active else C["sidebar_text"],
            font=font(10, "bold" if self._active else "normal")
        )
        self.bar.configure(bg="#818cf8" if self._active else background)


# --------------------------------------------------
# APPLICATION WINDOW
# --------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        apply_theme(self)

        self.title(APP_NAME)
        self.minsize(px(1100), px(680))
        self._centre(px(1380), px(860))

        self._results = queue.Queue()
        self._pending = 0
        self._busy_since = None
        self._toast = None
        self._toast_job = None

        self._closing = False
        self._nav = {}
        self._pages = {}
        self._current = None

        self._build_layout()
        self._bind_keys()

        self.after(40, self._poll)
        self.after(100, self._start)

    def destroy(self):
        self._closing = True
        super().destroy()

    def _centre(self, width, height):
        x = max((self.winfo_screenwidth() - width) // 2, 0)
        y = max((self.winfo_screenheight() - height) // 3, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    # ---------- layout ----------

    def _build_layout(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = tk.Frame(self, bg=C["sidebar"], width=px(236))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=C["sidebar"])
        brand.pack(fill="x", padx=22, pady=(26, 22))
        tk.Label(
            brand, text="Retailer", bg=C["sidebar"], fg="#ffffff",
            font=font(18, "bold")
        ).pack(anchor="w")
        tk.Label(
            brand, text="DATABASE SYSTEM", bg=C["sidebar"],
            fg=C["sidebar_muted"], font=font(8, "bold")
        ).pack(anchor="w")

        for section, items in NAVIGATION:
            tk.Label(
                sidebar, text=section, bg=C["sidebar"],
                fg=C["sidebar_muted"], font=font(8, "bold"), anchor="w"
            ).pack(fill="x", padx=22, pady=(14, 4))

            for label, page_class in items:
                item = NavItem(
                    sidebar, label, lambda key=label: self.show_page(key)
                )
                item.pack(fill="x")
                self._nav[label] = (item, page_class)

        footer = tk.Frame(sidebar, bg=C["sidebar"])
        footer.pack(side="bottom", fill="x", padx=22, pady=20)

        self.status_dot = tk.Label(
            footer, text="●  Not connected", bg=C["sidebar"],
            fg=C["sidebar_muted"], font=font(9, "bold"), anchor="w"
        )
        self.status_dot.pack(fill="x")

        self.status_detail = tk.Label(
            footer, text="", bg=C["sidebar"], fg=C["sidebar_muted"],
            font=font(8), anchor="w", justify="left", wraplength=px(190)
        )
        self.status_detail.pack(fill="x", pady=(2, 8))

        change = tk.Label(
            footer, text="Change connection", bg=C["sidebar"],
            fg="#818cf8", font=font(9), anchor="w", cursor="hand2"
        )
        change.pack(fill="x")
        change.bind("<Button-1>", lambda _e: self._sign_in())

        main = ttk.Frame(self)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        self.progress = ttk.Progressbar(
            main, mode="indeterminate", style="Thin.Horizontal.TProgressbar"
        )
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress.grid_remove()

        self.page_area = ttk.Frame(main)
        self.page_area.grid(row=1, column=0, sticky="nsew")

    def _bind_keys(self):
        self.bind("<F5>", lambda _e: self._page_call("refresh"))
        self.bind("<Control-f>", lambda _e: self._page_call("focus_search"))
        self.bind("<Control-r>", lambda _e: self._page_call("refresh"))

        names = [label for _, items in NAVIGATION for label, _ in items]

        for number, name in enumerate(names, start=1):
            self.bind(f"<Control-Key-{number}>",
                      lambda _e, key=name: self.show_page(key))

    def _page_call(self, method):
        page = self._pages.get(self._current)

        if page is not None:
            getattr(page, method)()

    # ---------- navigation ----------

    def show_page(self, key):
        if key not in self._nav:
            return

        if self._current in self._pages:
            self._pages[self._current].pack_forget()

        if key not in self._pages:
            self._pages[key] = self._nav[key][1](self.page_area, self)

        self._current = key

        for label, (item, _) in self._nav.items():
            item.set_active(label == key)

        page = self._pages[key]
        page.pack(fill="both", expand=True)
        page.on_show()

    # ---------- background work ----------

    def run(self, work, done=None, fail=None):
        """
        Run work() in a thread so the window stays responsive, then call
        done(result) here in the interface thread. If work() raises, fail(error)
        is called instead; without `fail` the error is shown to the user.
        """

        if self._pending == 0:
            self._busy_since = time.monotonic()

        self._pending += 1

        def target():
            try:
                result = work()
            except Exception as error:                  # noqa: BLE001
                self._results.put((done, fail, None, error))
            else:
                self._results.put((done, fail, result, None))

        threading.Thread(target=target, daemon=True).start()

    def _poll(self):
        if self._closing:
            return

        # Reschedule first: a callback may open a modal dialog, which runs a
        # nested event loop, and that dialog's own background work must still
        # be delivered while it is open.
        self.after(40, self._poll)

        try:
            while not self._closing:
                done, fail, result, error = self._results.get_nowait()
                self._pending -= 1

                if error is None:
                    self._call(done, result)
                elif fail is not None:
                    self._call(fail, error)
                else:
                    self._report(error)
        except queue.Empty:
            pass

        if not self._closing:
            self._update_busy()

    def _call(self, callback, argument):
        if callback is None:
            return

        try:
            callback(argument)
        except tk.TclError:
            # A window closed while its work was running; nothing to update.
            pass
        except Exception as error:                      # noqa: BLE001
            self._report(error)

    def _update_busy(self):
        busy = self._pending > 0
        showing = bool(self.progress.winfo_ismapped())

        # Only show the bar for work that takes a moment.
        if busy and not showing and (
                time.monotonic() - (self._busy_since or 0) > 0.2):
            self.progress.grid()
            self.progress.start(12)
        elif not busy and showing:
            self.progress.stop()
            self.progress.grid_remove()

    # ---------- messages ----------

    def _report(self, error):
        if isinstance(error, UserError):
            self.show_error(str(error), "Can’t do that", warning=True)
        elif isinstance(error, DatabaseUnavailableError):
            self.show_error(
                f"{error}\n\nUse “Change connection” in the "
                "sidebar to update the details.", "Database unavailable"
            )
        elif isinstance(error, oracledb.Error):
            self.show_error(describe_db_error(error), "Database error")
        else:
            traceback.print_exception(error)
            self.show_error(
                f"Something unexpected went wrong:\n{error}", "Error"
            )

    def show_error(self, message, title="Something went wrong",
                   warning=False):
        show = messagebox.showwarning if warning else messagebox.showerror
        show(title, message, parent=self)

    def toast(self, message, kind="success"):
        self._clear_toast()

        self._toast = tk.Label(
            self, text=message, bg=TOAST_COLOURS.get(kind, C["success"]),
            fg="#ffffff", font=font(10, "bold"), padx=18, pady=11
        )
        self._toast.place(relx=1.0, rely=1.0, x=-px(28), y=-px(28),
                          anchor="se")
        self._toast.lift()
        self._toast_job = self.after(3800, self._clear_toast)

    def _clear_toast(self):
        if self._toast_job is not None:
            self.after_cancel(self._toast_job)
            self._toast_job = None

        if self._toast is not None:
            self._toast.destroy()
            self._toast = None

    # ---------- connecting ----------

    def _start(self):
        self.run(
            lambda: try_connect(current_settings()),
            lambda _r: self._connected(),
            lambda error: self._sign_in(
                f"Could not connect: {self._first_line(error)}", quit_on_cancel=True
            )
        )

    @staticmethod
    def _first_line(error):
        return (str(error).strip().splitlines() or ["unknown error"])[0]

    def _sign_in(self, message=None, quit_on_cancel=False):
        settings = ConnectDialog(
            self, self, current_settings(), try_connect, message
        ).show()

        if settings is None:
            if quit_on_cancel:
                self.destroy()

            return

        apply_settings(settings)
        self._connected()

    def _connected(self):
        settings = current_settings()

        self.status_dot.configure(
            text="●  Connected", fg="#34d399"
        )
        self.status_detail.configure(
            text=f"{settings['user']}@{settings['host']}\n"
                 f"port {settings['port']} · {settings['service']}"
        )

        if self._current is None:
            self.show_page("Dashboard")
        else:
            self._page_call("refresh")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass

    App().mainloop()


if __name__ == "__main__":
    main()
