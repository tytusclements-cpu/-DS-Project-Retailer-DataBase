# gui_insights.py
# The dashboard (key numbers and charts) and the reports screen.

import csv
import tkinter as tk
from tkinter import filedialog, ttk

import database
import reports
from cli_utils import UserError, fmt_dt, money
from database import db_session
from gui_base import Page
from gui_theme import C, font, px
from gui_widgets import Card, DataTable, SearchBox

LOW_STOCK_LIMIT = 20


# --------------------------------------------------
# BAR CHART
# --------------------------------------------------

class BarChart(tk.Canvas):
    """Horizontal bars with a label on the left and the value on the right."""

    ROW = 34   # scaled in __init__

    def __init__(self, parent, color=None, empty="No data yet"):
        super().__init__(
            parent, bg=C["surface"], highlightthickness=0, height=px(120)
        )

        self._items = []
        self._row = px(self.ROW)
        self._color = color or C["accent"]
        self._empty = empty

        self.bind("<Configure>", lambda _e: self._draw())

    def set_data(self, items):
        """items: [(label, number, text shown beside the bar)]"""

        self._items = list(items)
        self._draw()

    def _draw(self):
        self.delete("all")
        width = self.winfo_width()

        if width <= 1:
            return

        if not self._items:
            self.create_text(
                width / 2, 50, text=self._empty, fill=C["faint"],
                font=font(10)
            )
            return

        label_width = min(px(170), width * 0.34)
        value_width = px(90)
        left = label_width + 12
        right = width - value_width
        biggest = max((v for _, v, _ in self._items), default=0) or 1

        for row, (label, value, text) in enumerate(self._items):
            y = row * self._row + self._row / 2
            shown = label if len(label) <= 24 else label[:23] + "…"

            self.create_text(
                0, y, text=shown, anchor="w", fill=C["text"], font=font(10)
            )

            span = max(right - left, 10)
            length = max(span * (value / biggest), 3 if value else 0)

            self.create_rectangle(
                left, y - 8, left + span, y + 8, fill=C["hover"], width=0
            )

            if length:
                self.create_rectangle(
                    left, y - 8, left + length, y + 8, fill=self._color,
                    width=0
                )

            self.create_text(
                width, y, text=text, anchor="e", fill=C["muted"],
                font=font(10, "bold")
            )

        self.configure(height=max(len(self._items) * self._row, px(60)))


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

class DashboardPage(Page):
    title = "Dashboard"
    subtitle = "A quick look at how the business is doing."

    KPIS = [
        ("revenue", "STORE REVENUE"),
        ("open_orders", "OPEN ONLINE ORDERS"),
        ("products", "PRODUCTS"),
        ("customers", "CUSTOMERS"),
        ("units", "UNITS IN STOCK"),
        ("low", f"LOW STOCK (≤ {LOW_STOCK_LIMIT})"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, app)

        body = self.content
        body.columnconfigure((0, 1), weight=1, uniform="half")
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=1)

        strip = ttk.Frame(body)
        strip.grid(row=0, column=0, columnspan=2, sticky="ew",
                   pady=(0, 16))
        strip.columnconfigure(tuple(range(len(self.KPIS))), weight=1,
                              uniform="kpi")

        self._kpi = {}

        for column, (key, label) in enumerate(self.KPIS):
            card = Card(strip)
            card.grid(row=0, column=column, sticky="ew",
                      padx=(0 if column == 0 else 12, 0))

            inner = ttk.Frame(card, style="Card.TFrame", padding=(16, 14))
            inner.pack(fill="both")

            ttk.Label(inner, text=label, style="KPILabel.TLabel").pack(
                anchor="w"
            )
            value = ttk.Label(inner, text="—", style="KPIValue.TLabel")
            value.pack(anchor="w", pady=(4, 0))
            self._kpi[key] = value

        self.revenue_chart = BarChart(self._panel(body, 1, 0,
                                                  "Revenue by store"))
        self.revenue_chart.pack(fill="x", padx=18, pady=(0, 14))

        self.sales_table = DataTable(
            self._panel(body, 1, 1, "Recent sales"),
            [("Sale", 55, "e"), ("Date", 120), ("Store", 150, "w", True),
             ("Total", 90, "e")], compact=True, footer=False,
            empty_text="No sales yet"
        )
        self.sales_table.pack(fill="both", expand=True)

        self.low_table = DataTable(
            self._panel(body, 2, 0, "Lowest stock"),
            [("Store", 150, "w", True), ("Product", 200, "w", True),
             ("Qty", 70, "e")], compact=True, footer=False,
            empty_text="No inventory yet"
        )
        self.low_table.pack(fill="both", expand=True)

        self.status_chart = BarChart(
            self._panel(body, 2, 1, "Online orders by status"),
            color=C["success"], empty="No online orders yet"
        )
        self.status_chart.pack(fill="x", padx=18, pady=(0, 14))

    @staticmethod
    def _panel(parent, row, column, heading):
        card = Card(parent)
        card.grid(row=row, column=column, sticky="nsew",
                  padx=(0, 8) if column == 0 else (8, 0),
                  pady=(0, 16) if row == 1 else 0)

        ttk.Label(card, text=heading, style="CardTitle.TLabel").pack(
            anchor="w", padx=18, pady=(14, 10)
        )

        return card

    def refresh(self):
        self.app.run(self._fetch, self._show)

    def _fetch(self):
        with db_session() as cursor:
            cursor.execute("""
                SELECT (SELECT NVL(SUM(quantity * unit_price), 0)
                        FROM Sale_Items),
                       (SELECT COUNT(*) FROM Web_Orders
                        WHERE order_status NOT IN ('Delivered', 'Cancelled')),
                       (SELECT COUNT(*) FROM Products),
                       (SELECT COUNT(*) FROM Customers),
                       (SELECT NVL(SUM(quantity), 0) FROM Inventory),
                       (SELECT COUNT(*) FROM Inventory
                        WHERE quantity <= :low)
                FROM dual
            """, {"low": LOW_STOCK_LIMIT})
            kpis = cursor.fetchone()

            cursor.execute("""
                SELECT * FROM (
                    SELECT s.store_name,
                           SUM(si.quantity * si.unit_price) AS revenue
                    FROM Stores s
                    JOIN Sales sa ON s.store_id = sa.store_id
                    JOIN Sale_Items si ON sa.sale_id = si.sale_id
                    GROUP BY s.store_id, s.store_name
                    ORDER BY revenue DESC
                ) WHERE ROWNUM <= 6
            """)
            revenue = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM (
                    SELECT sa.sale_id, sa.sale_date, st.store_name,
                           NVL(SUM(si.quantity * si.unit_price), 0)
                    FROM Sales sa
                    JOIN Stores st ON sa.store_id = st.store_id
                    LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
                    GROUP BY sa.sale_id, sa.sale_date, st.store_name
                    ORDER BY sa.sale_date DESC, sa.sale_id DESC
                ) WHERE ROWNUM <= 8
            """)
            recent = cursor.fetchall()

            cursor.execute("""
                SELECT * FROM (
                    SELECT s.store_name, p.product_name, i.quantity
                    FROM Inventory i
                    JOIN Stores s ON i.store_id = s.store_id
                    JOIN Products p ON i.product_id = p.product_id
                    ORDER BY i.quantity, s.store_name, p.product_name
                ) WHERE ROWNUM <= 8
            """)
            lowest = cursor.fetchall()

            cursor.execute("""
                SELECT order_status, COUNT(*)
                FROM Web_Orders
                GROUP BY order_status
                ORDER BY COUNT(*) DESC, order_status
            """)
            statuses = cursor.fetchall()

        return kpis, revenue, recent, lowest, statuses

    def _show(self, data):
        kpis, revenue, recent, lowest, statuses = data

        self._kpi["revenue"].configure(text=money(kpis[0]))
        self._kpi["open_orders"].configure(text=f"{kpis[1]:,}")
        self._kpi["products"].configure(text=f"{kpis[2]:,}")
        self._kpi["customers"].configure(text=f"{kpis[3]:,}")
        self._kpi["units"].configure(text=f"{kpis[4]:,}")
        self._kpi["low"].configure(
            text=f"{kpis[5]:,}",
            foreground=C["warning"] if kpis[5] else C["text"]
        )

        self.revenue_chart.set_data(
            [(name, total, money(total)) for name, total in revenue]
        )
        self.status_chart.set_data(
            [(status, count, f"{count:,}") for status, count in statuses]
        )
        self.sales_table.set_rows(
            [(r[0], fmt_dt(r[1]), r[2], money(r[3])) for r in recent]
        )
        self.low_table.set_rows(
            lowest,
            tags=["out" if r[2] == 0 else
                  "low" if r[2] <= LOW_STOCK_LIMIT else None for r in lowest]
        )


# --------------------------------------------------
# REPORTS
# --------------------------------------------------

# name, description, function in reports.py, columns, how to show each column
REPORTS = [
    ("Top products by store",
     "The 20 best-selling products at each store, ranked by units sold.",
     reports.top_products_by_store,
     [("Store", 200, "w", True), ("Product", 260, "w", True),
      ("Units sold", 100, "e"), ("Rank", 70, "e")],
     [None, None, None, None]),

    ("Top 5 stores this year",
     "The five stores with the highest sales revenue this calendar year.",
     reports.top_stores_by_sales,
     [("Store ID", 80, "e"), ("Store", 280, "w", True),
      ("Revenue", 130, "e")],
     [None, None, "money"]),

    ("Coca-Cola vs Pepsi",
     "Units sold and revenue for each brand at every store.",
     reports.compare_coke_pepsi,
     [("Store", 240, "w", True), ("Brand", 160), ("Units sold", 100, "e"),
      ("Revenue", 120, "e")],
     [None, None, None, "money"]),

    ("Bought together with milk",
     "Products that appeared in the same sale as milk.",
     reports.products_bought_with_milk,
     [("Product", 400, "w", True)],
     [None]),

    ("Inventory by store",
     "Current stock of every product at every store.",
     reports.inventory_report,
     [("Store", 240, "w", True), ("Product", 300, "w", True),
      ("In stock", 100, "e")],
     [None, None, None]),

    ("Customer sales history",
     "Every store sale linked to a customer.",
     reports.customer_sales_history,
     [("Customer ID", 90, "e"), ("Customer", 180, "w", True),
      ("Sale ID", 70, "e"), ("Date", 130), ("Store", 180, "w", True),
      ("Total", 100, "e")],
     [None, None, None, "date", None, "money"]),

    ("Online order report",
     "Online orders with customer, status and order total.",
     reports.online_order_report,
     [("Order ID", 80, "e"), ("Customer", 220, "w", True), ("Date", 130),
      ("Status", 110), ("Total", 100, "e")],
     [None, None, "date", None, "money"]),

    ("Vendor reorders",
     "Reorders with vendor, store, product and quantity.",
     reports.vendor_reorder_report,
     [("Reorder ID", 85, "e"), ("Vendor", 160, "w", True),
      ("Store", 160, "w", True), ("Product", 180, "w", True),
      ("Qty", 60, "e"), ("Date", 130), ("Status", 110)],
     [None, None, None, None, None, "date", None]),

    ("Shipments",
     "Shipments received against reorders, with quantities.",
     reports.shipment_report,
     [("Shipment ID", 90, "e"), ("Reorder ID", 85, "e"), ("Date", 130),
      ("Status", 110), ("Product", 260, "w", True), ("Qty shipped", 90, "e")],
     [None, None, "date", None, None, None]),
]


def _display(value, kind):
    if kind == "money":
        return money(value)

    if kind == "date":
        return fmt_dt(value)

    return value


def _export_value(value, kind):
    if kind == "money":
        return "" if value is None else f"{float(value):.2f}"

    if kind == "date":
        return fmt_dt(value)

    return "" if value is None else value


class ReportsPage(Page):
    title = "Reports"
    subtitle = "Ready-made reports. Click a column to sort, export to CSV."

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self._raw = []
        self._current = None
        self._token = 0

        body = self.content
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        menu = Card(body, width=px(270))
        menu.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        menu.pack_propagate(False)
        menu.grid_propagate(False)

        self.menu = DataTable(
            menu, [("Report", 250, "w", True)], footer=False,
            on_select=self._picked, key_columns=(0,)
        )
        self.menu.pack(fill="both", expand=True)
        self.menu.set_rows([(name,) for name, *_ in REPORTS])

        self.result_card = Card(body)
        self.result_card.grid(row=0, column=1, sticky="nsew")
        self.result_card.columnconfigure(0, weight=1)
        self.result_card.rowconfigure(2, weight=1)

        top = ttk.Frame(self.result_card, style="Card.TFrame",
                        padding=(18, 14, 18, 8))
        top.grid(row=0, column=0, sticky="ew")

        titles = ttk.Frame(top, style="Card.TFrame")
        titles.pack(side="left")
        self.report_title = ttk.Label(
            titles, text="Choose a report", style="CardTitle.TLabel"
        )
        self.report_title.pack(anchor="w")
        self.report_note = ttk.Label(
            titles, text="Pick one from the list on the left.",
            style="CardMuted.TLabel", wraplength=px(380), justify="left"
        )
        self.report_note.pack(anchor="w")

        self.export_button = ttk.Button(
            top, text="Export CSV", command=self._export, state="disabled"
        )
        self.export_button.pack(side="right")

        self.search = SearchBox(top, self._filter)
        self.search.pack(side="right", padx=(0, 12))

        tk.Frame(self.result_card, bg=C["border"], height=1).grid(
            row=1, column=0, sticky="ew"
        )

        self.table_holder = tk.Frame(self.result_card, bg=C["surface"])
        self.table_holder.grid(row=2, column=0, sticky="nsew")
        self.table_holder.columnconfigure(0, weight=1)
        self.table_holder.rowconfigure(0, weight=1)

        self.table = None

    def on_show(self):
        if self._current is None:
            self.menu.tree.selection_set("0")
        else:
            self._run()

    def refresh(self):
        if self._current is not None:
            self._run()

    def focus_search(self):
        self.search.focus()

    def _picked(self, row):
        if row is None:
            return

        names = [name for name, *_ in REPORTS]
        self._current = names.index(row[0])
        self.search.var.set("")
        self._run()

    def _filter(self, text):
        if self.table is not None:
            self.table.set_filter(text)

    def _run(self):
        name, note, function, columns, kinds = REPORTS[self._current]
        self._token += 1
        token = self._token

        self.report_title.configure(text=name)
        self.report_note.configure(text=note)

        def work():
            rows = function()

            if not rows and database.last_query_error:
                raise UserError(
                    f"The report could not be run: "
                    f"{database.last_query_error.splitlines()[0]}"
                )

            return rows

        def done(rows):
            if token != self._token:
                return

            self._raw = [tuple(r) for r in rows]

            if self.table is not None:
                self.table.destroy()

            self.table = DataTable(
                self.table_holder, columns, footer=True,
                key_columns=(0,), empty_text="This report has no rows yet"
            )
            self.table.grid(row=0, column=0, sticky="nsew")
            self.table.set_rows([
                tuple(_display(v, k) for v, k in zip(row, kinds))
                for row in self._raw
            ])
            self.table.set_filter(self.search.var.get())
            self.export_button.state(["!disabled"])

        self.app.run(work, done)

    def _export(self):
        if self._current is None:
            return

        name, _note, _function, columns, kinds = REPORTS[self._current]

        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), title="Export report",
            defaultextension=".csv", initialfile=f"{name}.csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")]
        )

        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow([c[0] for c in columns])

                for row in self._raw:
                    writer.writerow(
                        [_export_value(v, k) for v, k in zip(row, kinds)]
                    )
        except OSError as error:
            self.app.show_error(f"Could not save the file: {error}")
            return

        self.app.toast(f"Exported {len(self._raw):,} rows.")
