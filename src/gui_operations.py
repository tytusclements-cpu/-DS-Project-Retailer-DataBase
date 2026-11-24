# gui_operations.py
# Day-to-day screens: inventory, sales, online orders and vendor reorders.

import tkinter as tk
from tkinter import messagebox, ttk

from cli_utils import UserError, fmt_dt, money, require_row
from database import db_session
from gui_base import (
    ListDetail, Page, PanelPage, load_choices,
)
from gui_dialogs import CartDialog, FormDialog
from gui_widgets import ChoiceBox, Tabs
from inventory import INVENTORY_SELECT, MAX_QUANTITY
from orders import ORDER_TRANSITIONS, REORDER_TRANSITIONS
from sales import SALES_LIST_SQL, _sell_item

DEFAULT_LOW_STOCK = 20


def _confirm(widget, title, message):
    return messagebox.askyesno(
        title, message, icon="warning", parent=widget.winfo_toplevel()
    )


# --------------------------------------------------
# INVENTORY
# --------------------------------------------------

class InventoryPanel(ListDetail):
    columns = [("Store ID", 75, "e"), ("Store", 220, "w", True),
               ("Product ID", 90, "e"), ("Product", 300, "w", True),
               ("Quantity", 100, "e")]
    key_columns = (0, 2)
    detail_width = None
    filters_inline = False
    empty_text = "No inventory records found"

    def __init__(self, parent, app):
        self._filters = {"store_id": None, "low": False,
                         "threshold": DEFAULT_LOW_STOCK}
        self._store_choices = []
        self._last_threshold = DEFAULT_LOW_STOCK

        super().__init__(parent, app)

    # ---------- toolbar ----------

    def build_filters(self, bar):
        self.store_box = ChoiceBox(bar, blank="All stores", width=24)
        self.store_box.pack(side="left", padx=(16, 0))
        self.store_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.low_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bar, text="Low stock only", variable=self.low_only,
            style="Card.TCheckbutton", command=self.refresh
        ).pack(side="left", padx=(16, 0))

        ttk.Label(
            bar, text="at or below", style="CardMuted.TLabel"
        ).pack(side="left", padx=(8, 4))

        self.threshold = ttk.Spinbox(
            bar, from_=0, to=MAX_QUANTITY, width=6,
            command=self._threshold_changed
        )
        self.threshold.set(str(DEFAULT_LOW_STOCK))
        self.threshold.pack(side="left")
        self.threshold.bind("<Return>", lambda _e: self._threshold_changed())
        self.threshold.bind("<FocusOut>", lambda _e: self._threshold_changed())

    def _threshold_changed(self):
        if self._read_filters()["threshold"] != self._last_threshold:
            self.refresh()

    def buttons(self):
        return [
            ("+  Add stock record", self.add, "Accent.TButton", False),
            ("Set quantity", self.set_quantity, "TButton", True),
            ("Adjust +/−", self.adjust, "TButton", True),
            ("Delete", self.delete, "Danger.TButton", True),
        ]

    def activate(self, _row):
        self.set_quantity()

    # ---------- list ----------

    def _read_filters(self):
        try:
            store_id = self.store_box.value()
        except ValueError:
            store_id = None

        try:
            threshold = max(0, min(int(self.threshold.get()), MAX_QUANTITY))
        except ValueError:
            threshold = DEFAULT_LOW_STOCK

        return {"store_id": store_id, "low": self.low_only.get(),
                "threshold": threshold}

    def refresh(self, select_key=None):
        self._filters = self._read_filters()
        self._last_threshold = self._filters["threshold"]
        super().refresh(select_key)

    def fetch_rows(self):
        filters = self._filters
        conditions, params = [], {}

        if filters["store_id"] is not None:
            conditions.append("i.store_id = :store_id")
            params["store_id"] = filters["store_id"]

        if filters["low"]:
            conditions.append("i.quantity <= :threshold")
            params["threshold"] = filters["threshold"]

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""

        with db_session() as cursor:
            cursor.execute(
                INVENTORY_SELECT + where +
                " ORDER BY s.store_name, p.product_name", params
            )
            rows = cursor.fetchall()
            self._store_choices = load_choices(cursor, "stores")["stores"]

        return rows

    def row_tag(self, row):
        if row[4] == 0:
            return "out"

        return "low" if row[4] <= self._filters["threshold"] else None

    def after_load(self, rows):
        self.store_box.set_choices(self._store_choices)
        self.table.set_extra(f"{sum(r[4] for r in rows):,} units")

    # ---------- actions ----------

    def _key(self):
        row = self.table.selected()
        return None if row is None else (row[0], row[2])

    def add(self):
        def work():
            with db_session() as cursor:
                return load_choices(cursor, "stores", "products")

        self.app.run(work, self._add_dialog)

    def _add_dialog(self, choices):
        values = FormDialog(self, "Add stock record", [
            {"key": "store_id", "label": "Store", "kind": "choice",
             "choices": choices["stores"]},
            {"key": "product_id", "label": "Product", "kind": "choice",
             "choices": choices["products"]},
            {"key": "quantity", "label": "Quantity", "kind": "int",
             "minimum": 0, "maximum": MAX_QUANTITY, "value": 0},
        ], submit="Add record").show()

        if values is None:
            return

        def work():
            with db_session() as cursor:
                cursor.execute("""
                    INSERT INTO Inventory (store_id, product_id, quantity)
                    VALUES (:store_id, :product_id, :quantity)
                """, values)

        self.app.run(work, lambda _r: self._done(
            "Stock record added.", (values["store_id"], values["product_id"])
        ))

    def set_quantity(self):
        row = self.table.selected()

        if row is None:
            return

        store_id, _, product_id, product, quantity = row

        values = FormDialog(
            self, "Set quantity", [
                {"key": "quantity", "label": "New quantity", "kind": "int",
                 "minimum": 0, "maximum": MAX_QUANTITY, "value": quantity},
            ], submit="Save", intro=f"{product} — currently {quantity:,}."
        ).show()

        if values is None:
            return

        def work():
            with db_session() as cursor:
                cursor.execute("""
                    UPDATE Inventory SET quantity = :quantity
                    WHERE store_id = :store_id AND product_id = :product_id
                """, {**values, "store_id": store_id,
                      "product_id": product_id})

                if cursor.rowcount == 0:
                    raise UserError(
                        "Inventory record not found for that store and "
                        "product."
                    )

        self.app.run(work, lambda _r: self._done(
            "Quantity updated.", (store_id, product_id)
        ))

    def adjust(self):
        row = self.table.selected()

        if row is None:
            return

        store_id, store, product_id, product, quantity = row

        values = FormDialog(
            self, "Adjust quantity", [
                {"key": "change", "label": "Change in quantity",
                 "kind": "int", "minimum": -MAX_QUANTITY,
                 "maximum": MAX_QUANTITY,
                 "hint": "Positive receives stock, negative removes it "
                         "(for example 25 or -5)."},
            ], submit="Apply",
            intro=f"{product} at {store} — currently {quantity:,}."
        ).show()

        if values is None:
            return

        change = values["change"]

        if change == 0:
            self.app.toast("A change of 0 does nothing.", "warning")
            return

        def work():
            with db_session() as cursor:
                # Check-and-update in one statement so stock cannot go
                # negative even with several users at once.
                cursor.execute("""
                    UPDATE Inventory SET quantity = quantity + :change
                    WHERE store_id = :store_id AND product_id = :product_id
                      AND quantity + :change >= 0
                """, {"change": change, "store_id": store_id,
                      "product_id": product_id})
                applied = cursor.rowcount > 0

                cursor.execute("""
                    SELECT quantity FROM Inventory
                    WHERE store_id = :store_id AND product_id = :product_id
                """, {"store_id": store_id, "product_id": product_id})
                current = cursor.fetchone()

            if current is None:
                raise UserError(
                    "Inventory record not found for that store and product."
                )

            return applied, current[0]

        def done(result):
            applied, new_quantity = result

            if applied:
                self._done(f"New quantity: {new_quantity:,}.",
                           (store_id, product_id))
                return

            self.app.show_error(
                f"Cannot remove {-change:,} units: only {new_quantity:,} "
                "in stock."
            )
            self.refresh(select_key=(store_id, product_id))

        self.app.run(work, done)

    def delete(self):
        row = self.table.selected()

        if row is None:
            return

        store_id, store, product_id, product, _ = row

        if not _confirm(self, "Delete stock record",
                        f"Remove {product} from {store}?\n\n"
                        "This cannot be undone."):
            return

        def work():
            with db_session() as cursor:
                cursor.execute("""
                    DELETE FROM Inventory
                    WHERE store_id = :store_id AND product_id = :product_id
                """, {"store_id": store_id, "product_id": product_id})

                if cursor.rowcount == 0:
                    raise UserError(
                        "Inventory record not found for that store and "
                        "product."
                    )

        self.app.run(work, lambda _r: self._done("Stock record deleted."))

    def _done(self, message, key=None):
        self.app.toast(message)
        self.refresh(select_key=key)


class InventoryPage(PanelPage):
    title = "Inventory"
    subtitle = "Stock levels by store. Rows in amber are running low."
    panel_class = InventoryPanel


# --------------------------------------------------
# SALES
# --------------------------------------------------

def _stocked_products(store_id):
    """(id, name, price, quantity) for everything in stock at a store."""

    with db_session() as cursor:
        cursor.execute("""
            SELECT p.product_id, p.product_name, p.unit_price, i.quantity
            FROM Inventory i
            JOIN Products p ON i.product_id = p.product_id
            WHERE i.store_id = :store_id AND i.quantity > 0
            ORDER BY p.product_name
        """, {"store_id": store_id})
        return cursor.fetchall()


class SalesPanel(ListDetail):
    columns = [("Sale ID", 70, "e"), ("Date", 130), ("Store", 190, "w", True),
               ("Customer", 170, "w", True), ("Units", 60, "e"),
               ("Total", 95, "e")]
    empty_text = "No sales recorded yet"
    detail_empty = "Select a sale to see what was sold."

    def buttons(self):
        return [
            ("+  New sale", self.new_sale, "Accent.TButton", False),
            ("Add item", self.add_item, "TButton", True),
            ("Void sale", self.void, "Danger.TButton", True),
        ]

    # ---------- list ----------

    def fetch_rows(self):
        with db_session() as cursor:
            cursor.execute(SALES_LIST_SQL.format(where=""))
            rows = cursor.fetchall()

        self._grand_total = sum(r[5] for r in rows)

        return [
            (r[0], fmt_dt(r[1]), r[2], r[3] or "Anonymous", r[4],
             money(r[5]))
            for r in rows
        ]

    def after_load(self, rows):
        self.table.set_extra(f"{money(self._grand_total)} combined")

    def load_details(self, row):
        sale_id = int(row[0])

        with db_session() as cursor:
            sale = require_row(
                cursor,
                """
                SELECT sa.sale_date, st.store_name,
                       NVL2(c.customer_id,
                            c.first_name || ' ' || c.last_name, NULL)
                FROM Sales sa
                JOIN Stores st ON sa.store_id = st.store_id
                LEFT JOIN Customers c ON sa.customer_id = c.customer_id
                WHERE sa.sale_id = :id
                """,
                {"id": sale_id}, f"Sale {sale_id} not found."
            )

            cursor.execute("""
                SELECT p.product_name, si.quantity, si.unit_price,
                       si.quantity * si.unit_price
                FROM Sale_Items si
                JOIN Products p ON si.product_id = p.product_id
                WHERE si.sale_id = :id
                ORDER BY p.product_name
            """, {"id": sale_id})
            items = cursor.fetchall()

        return {
            "title": f"Sale #{sale_id}",
            "subtitle": fmt_dt(sale[0]),
            "fields": [
                ("Store", sale[1]),
                ("Customer", sale[2] or "Anonymous"),
                ("Units", sum(r[1] for r in items)),
                ("Total", money(sum(r[3] for r in items))),
            ],
            "tables": [(
                "Items sold",
                [("Product", 120, "w", True), ("Qty", 40, "e"),
                 ("Price", 65, "e"), ("Subtotal", 75, "e")],
                [(r[0], r[1], money(r[2]), money(r[3])) for r in items]
            )],
        }

    # ---------- new sale ----------

    def new_sale(self):
        def work():
            with db_session() as cursor:
                return load_choices(cursor, "stores", "customers")

        self.app.run(work, self._new_sale_dialog)

    def _new_sale_dialog(self, choices):
        if not choices["stores"]:
            self.app.show_error("Add a store before recording a sale.")
            return

        def load_products(store_id):
            return _stocked_products(store_id)

        result = CartDialog(
            self, self.app, "New sale",
            [{"key": "store_id", "label": "Store", "kind": "choice",
              "choices": choices["stores"]},
             {"key": "customer_id", "label": "Customer", "kind": "choice",
              "choices": choices["customers"], "required": False,
              "blank": "Anonymous"}],
            load_products, driver="store_id", show_price=True,
            show_stock=True, submit="Complete sale"
        ).show()

        if result is None:
            return

        store_id = result["header"]["store_id"]
        customer_id = result["header"]["customer_id"]
        lines = result["lines"]

        def work():
            # All-or-nothing: the sale, its items and the stock changes.
            with db_session() as cursor:
                sale_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Sales (store_id, customer_id)
                    VALUES (:store_id, :customer_id)
                    RETURNING sale_id INTO :sale_id
                """, {"store_id": store_id, "customer_id": customer_id,
                      "sale_id": sale_id})
                new_id = sale_id.getvalue()[0]
                total = 0

                for product_id, quantity in lines.items():
                    price = _sell_item(
                        cursor, new_id, store_id, product_id, quantity
                    )
                    total += price * quantity

            return new_id, total

        self.app.run(work, lambda r: self._sold(*r))

    def _sold(self, sale_id, total):
        self.app.toast(f"Sale #{sale_id} recorded — {money(total)}.")
        self.refresh(select_key=(sale_id,))

    # ---------- existing sale ----------

    def add_item(self):
        sale_id = self.selected_id()

        if sale_id is None:
            return

        def work():
            with db_session() as cursor:
                store_id = require_row(
                    cursor, "SELECT store_id FROM Sales WHERE sale_id = :id",
                    {"id": sale_id}, f"Sale {sale_id} not found."
                )[0]

            return store_id, _stocked_products(store_id)

        self.app.run(work, lambda r: self._add_item_dialog(sale_id, *r))

    def _add_item_dialog(self, sale_id, store_id, products):
        if not products:
            self.app.show_error("This sale's store has nothing in stock.")
            return

        values = FormDialog(
            self, f"Add product to sale #{sale_id}", [
                {"key": "product_id", "label": "Product", "kind": "choice",
                 "choices": [
                     (pid, f"{name}  ·  {money(price)}  ·  "
                           f"{stock} in stock")
                     for pid, name, price, stock in products]},
                {"key": "quantity", "label": "Quantity", "kind": "int",
                 "minimum": 1, "maximum": 1_000_000, "value": 1},
            ], submit="Add to sale"
        ).show()

        if values is None:
            return

        def work():
            with db_session() as cursor:
                _sell_item(cursor, sale_id, store_id, values["product_id"],
                           values["quantity"])

        self.app.run(work, lambda _r: self._changed(
            f"Product added to sale #{sale_id}.", sale_id
        ))

    def void(self):
        sale_id = self.selected_id()

        if sale_id is None:
            return

        if not _confirm(self, "Void sale", f"Void sale #{sale_id} and put "
                        "its products back into stock?"):
            return

        def work():
            with db_session() as cursor:
                store_id = require_row(
                    cursor, "SELECT store_id FROM Sales WHERE sale_id = :id",
                    {"id": sale_id}, f"Sale {sale_id} not found."
                )[0]

                cursor.execute(
                    "SELECT product_id, quantity FROM Sale_Items "
                    "WHERE sale_id = :id", {"id": sale_id}
                )
                items = cursor.fetchall()

                for product_id, quantity in items:
                    # MERGE restores stock even if the row was deleted.
                    cursor.execute("""
                        MERGE INTO Inventory i
                        USING (SELECT :store_id AS store_id,
                                      :product_id AS product_id
                               FROM dual) src
                        ON (i.store_id = src.store_id
                            AND i.product_id = src.product_id)
                        WHEN MATCHED THEN
                            UPDATE SET i.quantity = i.quantity + :quantity
                        WHEN NOT MATCHED THEN
                            INSERT (store_id, product_id, quantity)
                            VALUES (src.store_id, src.product_id, :quantity)
                    """, {"store_id": store_id, "product_id": product_id,
                          "quantity": quantity})

                cursor.execute(
                    "DELETE FROM Sale_Items WHERE sale_id = :id",
                    {"id": sale_id}
                )
                cursor.execute(
                    "DELETE FROM Sales WHERE sale_id = :id", {"id": sale_id}
                )

            return len(items)

        self.app.run(work, lambda n: self._changed(
            f"Sale #{sale_id} voided; {n} product line(s) restored to stock."
        ))

    def _changed(self, message, key=None):
        self.app.toast(message)
        self.refresh(select_key=None if key is None else (key,))


class SalesPage(PanelPage):
    title = "Sales"
    subtitle = "Checkout transactions from your physical stores."
    panel_class = SalesPanel


# --------------------------------------------------
# STATUS-DRIVEN LISTS (online orders, vendor reorders)
# --------------------------------------------------

class StatusPanel(ListDetail):
    """
    A list with a status filter and a "Change status" action.
    Subclasses set the table/column names and the allowed transitions.
    """

    noun = "order"
    table_name = ""
    id_column = ""
    status_column = ""
    status_index = 3
    transitions = {}
    list_sql = ""            # must contain {where}
    filters_inline = False

    def __init__(self, parent, app):
        self._status_filter = None
        super().__init__(parent, app)

    def build_filters(self, bar):
        self.status_box = ChoiceBox(
            bar, [(s, s) for s in self.transitions], blank="All statuses",
            width=18, state="readonly"
        )
        self.status_box.pack(side="left", padx=(16, 0))
        self.status_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

    def refresh(self, select_key=None):
        try:
            self._status_filter = self.status_box.value()
        except ValueError:
            self._status_filter = None

        super().refresh(select_key)

    def fetch_rows(self):
        where, params = "", {}

        if self._status_filter:
            where = f"WHERE {self.status_column} = :status"
            params["status"] = self._status_filter

        with db_session() as cursor:
            cursor.execute(self.list_sql.format(where=where), params)
            return [self.format_row(r) for r in cursor.fetchall()]

    def format_row(self, row):
        return tuple(row)

    # ---------- status ----------

    def change_status(self):
        row = self.table.selected()

        if row is None:
            return

        record_id, current = int(row[0]), row[self.status_index]
        allowed = self.transitions.get(current, [])

        if not allowed:
            self.app.toast(
                f"Status “{current}” is final and cannot be "
                "changed.", "warning"
            )
            return

        values = FormDialog(
            self, f"Change {self.noun} status", [
                {"key": "status", "label": "New status", "kind": "choice",
                 "choices": [(s, s) for s in allowed], "value": allowed[0]},
            ], submit="Update status",
            intro=f"{self.noun.capitalize()} #{record_id} is currently "
                  f"{current}."
        ).show()

        if values is None:
            return

        new_status = values["status"]

        def work():
            with db_session() as cursor:
                # Re-check the old status so two users cannot both change it.
                cursor.execute(
                    f"UPDATE {self.table_name} "
                    f"SET {self.status_column} = :new_status "
                    f"WHERE {self.id_column} = :record_id "
                    f"AND {self.status_column} = :old_status",
                    {"new_status": new_status, "record_id": record_id,
                     "old_status": current}
                )

                if cursor.rowcount == 0:
                    raise UserError(
                        f"The {self.noun} was changed by someone else. "
                        "Please try again."
                    )

        self.app.run(work, lambda _r: self._status_changed(
            record_id, new_status
        ))

    def _status_changed(self, record_id, status):
        self.app.toast(f"{self.noun.capitalize()} #{record_id} is now "
                       f"{status}.")
        self.refresh(select_key=(record_id,))


# --------------------------------------------------
# ONLINE ORDERS
# --------------------------------------------------

class WebOrdersPanel(StatusPanel):
    noun = "order"
    table_name = "Web_Orders"
    id_column = "order_id"
    status_column = "order_status"
    status_index = 3
    transitions = ORDER_TRANSITIONS
    columns = [("Order ID", 75, "e"), ("Date", 130),
               ("Customer", 200, "w", True), ("Status", 100),
               ("Units", 60, "e"), ("Total", 95, "e")]
    empty_text = "No online orders found"
    detail_empty = "Select an order to see its products."
    list_sql = """
        SELECT wo.order_id,
               wo.order_date,
               c.first_name || ' ' || c.last_name,
               wo.order_status,
               NVL(SUM(woi.quantity), 0),
               NVL(SUM(woi.quantity * woi.unit_price), 0)
        FROM Web_Orders wo
        JOIN Customers c ON wo.customer_id = c.customer_id
        LEFT JOIN Web_Order_Items woi ON wo.order_id = woi.order_id
        {where}
        GROUP BY wo.order_id, wo.order_date, c.first_name, c.last_name,
                 wo.order_status
        ORDER BY wo.order_date DESC, wo.order_id DESC
    """

    def buttons(self):
        return [
            ("+  New order", self.new_order, "Accent.TButton", False),
            ("Add item", self.add_item, "TButton", True),
            ("Change status", self.change_status, "TButton", True),
            ("Delete", self.delete, "Danger.TButton", True),
        ]

    def format_row(self, row):
        return (row[0], fmt_dt(row[1]), row[2], row[3], row[4],
                money(row[5]))

    def load_details(self, row):
        order_id = int(row[0])

        with db_session() as cursor:
            order = require_row(
                cursor,
                """
                SELECT wo.order_date, wo.order_status, wo.customer_id,
                       c.first_name || ' ' || c.last_name
                FROM Web_Orders wo
                JOIN Customers c ON wo.customer_id = c.customer_id
                WHERE wo.order_id = :id
                """,
                {"id": order_id}, f"Order {order_id} not found."
            )

            cursor.execute("""
                SELECT p.product_name, oi.quantity, oi.unit_price,
                       oi.quantity * oi.unit_price
                FROM Web_Order_Items oi
                JOIN Products p ON oi.product_id = p.product_id
                WHERE oi.order_id = :id
                ORDER BY p.product_name
            """, {"id": order_id})
            items = cursor.fetchall()

        return {
            "title": f"Order #{order_id}",
            "subtitle": fmt_dt(order[0]),
            "fields": [
                ("Status", order[1]),
                ("Customer", f"{order[3]} (ID {order[2]})"),
                ("Units", sum(r[1] for r in items)),
                ("Total", money(sum(r[3] for r in items))),
            ],
            "tables": [(
                "Products",
                [("Product", 120, "w", True), ("Qty", 40, "e"),
                 ("Price", 65, "e"), ("Subtotal", 75, "e")],
                [(r[0], r[1], money(r[2]), money(r[3])) for r in items]
            )],
        }

    # ---------- new order ----------

    def new_order(self):
        def work():
            with db_session() as cursor:
                return load_choices(cursor, "customers")

        self.app.run(work, self._new_order_dialog)

    def _new_order_dialog(self, choices):
        if not choices["customers"]:
            self.app.show_error("Register a customer before creating an "
                                "online order.")
            return

        def load_products(_driver):
            with db_session() as cursor:
                cursor.execute(
                    "SELECT product_id, product_name, unit_price, NULL "
                    "FROM Products ORDER BY product_name"
                )
                return cursor.fetchall()

        result = CartDialog(
            self, self.app, "New online order",
            [{"key": "customer_id", "label": "Customer", "kind": "choice",
              "choices": choices["customers"], "wide": True}],
            load_products, show_price=True, submit="Place order",
            header_columns=1
        ).show()

        if result is None:
            return

        customer_id = result["header"]["customer_id"]
        lines = result["lines"]

        def work():
            with db_session() as cursor:
                order_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Web_Orders (customer_id, order_status)
                    VALUES (:customer_id, 'Pending')
                    RETURNING order_id INTO :order_id
                """, {"customer_id": customer_id, "order_id": order_id})
                new_id = order_id.getvalue()[0]

                for product_id, quantity in lines.items():
                    price = require_row(
                        cursor,
                        "SELECT unit_price FROM Products "
                        "WHERE product_id = :id",
                        {"id": product_id}, f"Product {product_id} not found."
                    )[0]

                    cursor.execute("""
                        INSERT INTO Web_Order_Items (
                            order_id, product_id, quantity, unit_price
                        )
                        VALUES (:order_id, :product_id, :quantity,
                                :unit_price)
                    """, {"order_id": new_id, "product_id": product_id,
                          "quantity": quantity, "unit_price": price})

            return new_id

        self.app.run(work, lambda new_id: self._changed(
            f"Order #{new_id} placed.", new_id
        ))

    # ---------- existing order ----------

    def add_item(self):
        order_id = self.selected_id()

        if order_id is None:
            return

        if self.table.selected()[self.status_index] != "Pending":
            self.app.toast("Products can only be added to pending orders.",
                           "warning")
            return

        def work():
            with db_session() as cursor:
                return load_choices(cursor, "products")["products"]

        self.app.run(work, lambda choices: self._add_item_dialog(
            order_id, choices
        ))

    def _add_item_dialog(self, order_id, choices):
        values = FormDialog(
            self, f"Add product to order #{order_id}", [
                {"key": "product_id", "label": "Product", "kind": "choice",
                 "choices": choices},
                {"key": "quantity", "label": "Quantity", "kind": "int",
                 "minimum": 1, "maximum": 1_000_000, "value": 1},
            ], submit="Add to order"
        ).show()

        if values is None:
            return

        def work():
            with db_session() as cursor:
                status = require_row(
                    cursor,
                    "SELECT order_status FROM Web_Orders "
                    "WHERE order_id = :id FOR UPDATE",
                    {"id": order_id}, f"Order {order_id} not found."
                )[0]

                if status != "Pending":
                    raise UserError(
                        "Products can only be added to pending orders."
                    )

                price = require_row(
                    cursor,
                    "SELECT unit_price FROM Products WHERE product_id = :id",
                    {"id": values["product_id"]}, "Product not found."
                )[0]

                cursor.execute("""
                    UPDATE Web_Order_Items SET quantity = quantity + :quantity
                    WHERE order_id = :order_id AND product_id = :product_id
                """, {**values, "order_id": order_id})

                if cursor.rowcount == 0:
                    cursor.execute("""
                        INSERT INTO Web_Order_Items (
                            order_id, product_id, quantity, unit_price
                        )
                        VALUES (:order_id, :product_id, :quantity,
                                :unit_price)
                    """, {**values, "order_id": order_id,
                          "unit_price": price})

        self.app.run(work, lambda _r: self._changed(
            f"Product added to order #{order_id}.", order_id
        ))

    def delete(self):
        order_id = self.selected_id()

        if order_id is None:
            return

        if not _confirm(self, "Delete order",
                        f"Delete order #{order_id} and its products?\n\n"
                        "This cannot be undone."):
            return

        def work():
            with db_session() as cursor:
                require_row(
                    cursor, "SELECT 1 FROM Web_Orders WHERE order_id = :id",
                    {"id": order_id}, f"Order {order_id} not found."
                )
                cursor.execute(
                    "DELETE FROM Web_Order_Items WHERE order_id = :id",
                    {"id": order_id}
                )
                cursor.execute(
                    "DELETE FROM Web_Orders WHERE order_id = :id",
                    {"id": order_id}
                )

        self.app.run(work, lambda _r: self._changed(
            f"Order #{order_id} deleted."
        ))

    def _changed(self, message, key=None):
        self.app.toast(message)
        self.refresh(select_key=None if key is None else (key,))


# --------------------------------------------------
# VENDOR REORDERS
# --------------------------------------------------

class ReordersPanel(StatusPanel):
    noun = "reorder"
    table_name = "Reorders"
    id_column = "reorder_id"
    status_column = "reorder_status"
    status_index = 4
    transitions = REORDER_TRANSITIONS
    columns = [("Reorder ID", 85, "e"), ("Date", 130),
               ("Vendor", 180, "w", True), ("Store", 180, "w", True),
               ("Status", 125), ("Units", 60, "e")]
    empty_text = "No vendor reorders found"
    detail_empty = "Select a reorder to see its products and shipments."
    list_sql = """
        SELECT r.reorder_id,
               r.reorder_date,
               v.vendor_name,
               s.store_name,
               r.reorder_status,
               NVL(SUM(ri.quantity), 0)
        FROM Reorders r
        JOIN Vendors v ON r.vendor_id = v.vendor_id
        JOIN Stores s ON r.store_id = s.store_id
        LEFT JOIN Reorder_Items ri ON r.reorder_id = ri.reorder_id
        {where}
        GROUP BY r.reorder_id, r.reorder_date, v.vendor_name,
                 s.store_name, r.reorder_status
        ORDER BY r.reorder_date DESC, r.reorder_id DESC
    """

    def buttons(self):
        return [
            ("+  New reorder", self.new_reorder, "Accent.TButton", False),
            ("Change status", self.change_status, "TButton", True),
        ]

    def format_row(self, row):
        return (row[0], fmt_dt(row[1]), row[2], row[3], row[4], row[5])

    def load_details(self, row):
        reorder_id = int(row[0])

        with db_session() as cursor:
            reorder = require_row(
                cursor,
                """
                SELECT r.reorder_date, r.reorder_status, v.vendor_name,
                       s.store_name
                FROM Reorders r
                JOIN Vendors v ON r.vendor_id = v.vendor_id
                JOIN Stores s ON r.store_id = s.store_id
                WHERE r.reorder_id = :id
                """,
                {"id": reorder_id}, f"Reorder {reorder_id} not found."
            )

            cursor.execute("""
                SELECT p.product_name, ri.quantity
                FROM Reorder_Items ri
                JOIN Products p ON ri.product_id = p.product_id
                WHERE ri.reorder_id = :id
                ORDER BY p.product_name
            """, {"id": reorder_id})
            items = cursor.fetchall()

            cursor.execute("""
                SELECT sh.shipment_id, sh.shipment_status, sh.shipment_date,
                       NVL(SUM(shi.quantity), 0)
                FROM Shipments sh
                LEFT JOIN Shipment_Items shi
                       ON sh.shipment_id = shi.shipment_id
                WHERE sh.reorder_id = :id
                GROUP BY sh.shipment_id, sh.shipment_status, sh.shipment_date
                ORDER BY sh.shipment_id
            """, {"id": reorder_id})
            shipments = cursor.fetchall()

        return {
            "title": f"Reorder #{reorder_id}",
            "subtitle": fmt_dt(reorder[0]),
            "fields": [
                ("Status", reorder[1]),
                ("Vendor", reorder[2]),
                ("Deliver to", reorder[3]),
                ("Units ordered", sum(r[1] for r in items)),
            ],
            "tables": [
                ("Products", [("Product", 220, "w", True),
                              ("Qty", 60, "e")], items),
                ("Shipments",
                 [("ID", 40, "e"), ("Status", 90, "w", True),
                  ("Date", 105), ("Units", 45, "e")],
                 [(r[0], r[1], fmt_dt(r[2]), r[3]) for r in shipments]),
            ],
        }

    def new_reorder(self):
        def work():
            with db_session() as cursor:
                return load_choices(cursor, "vendors", "stores")

        self.app.run(work, self._new_reorder_dialog)

    def _new_reorder_dialog(self, choices):
        if not choices["vendors"] or not choices["stores"]:
            self.app.show_error(
                "A reorder needs at least one vendor and one store."
            )
            return

        def load_products(_driver):
            with db_session() as cursor:
                cursor.execute(
                    "SELECT product_id, product_name, NULL, NULL "
                    "FROM Products ORDER BY product_name"
                )
                return cursor.fetchall()

        result = CartDialog(
            self, self.app, "New vendor reorder",
            [{"key": "vendor_id", "label": "Vendor", "kind": "choice",
              "choices": choices["vendors"]},
             {"key": "store_id", "label": "Deliver to store",
              "kind": "choice", "choices": choices["stores"]}],
            load_products, show_price=False, submit="Place reorder"
        ).show()

        if result is None:
            return

        vendor_id = result["header"]["vendor_id"]
        store_id = result["header"]["store_id"]
        lines = result["lines"]

        def work():
            with db_session() as cursor:
                reorder_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Reorders (vendor_id, store_id, reorder_status)
                    VALUES (:vendor_id, :store_id, 'Pending')
                    RETURNING reorder_id INTO :reorder_id
                """, {"vendor_id": vendor_id, "store_id": store_id,
                      "reorder_id": reorder_id})
                new_id = reorder_id.getvalue()[0]

                for product_id, quantity in lines.items():
                    cursor.execute("""
                        INSERT INTO Reorder_Items (
                            reorder_id, product_id, quantity
                        )
                        VALUES (:reorder_id, :product_id, :quantity)
                    """, {"reorder_id": new_id, "product_id": product_id,
                          "quantity": quantity})

            return new_id

        def done(new_id):
            self.app.toast(f"Reorder #{new_id} placed.")
            self.refresh(select_key=(new_id,))

        self.app.run(work, done)


class OrdersPage(Page):
    title = "Orders"
    subtitle = "Online customer orders and reorders from your vendors."

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.tabs = Tabs(
            self.content, ["Online orders", "Vendor reorders"],
            self._tab_changed
        )
        self.tabs.pack(anchor="w", pady=(0, 10))

        holder = ttk.Frame(self.content)
        holder.pack(fill="both", expand=True)
        holder.columnconfigure(0, weight=1)
        holder.rowconfigure(0, weight=1)

        self.panels = [WebOrdersPanel(holder, app), ReordersPanel(holder, app)]

        for panel in self.panels:
            panel.grid(row=0, column=0, sticky="nsew")

        self.panels[0].tkraise()

    def _tab_changed(self, index):
        self.panels[index].tkraise()
        self.panels[index].refresh()

    def refresh(self):
        self.panels[self.tabs.current].refresh()

    def focus_search(self):
        self.panels[self.tabs.current].search.focus()
