# gui_catalog.py
# Screens for the master data: products, stores, customers and vendors.

from cli_utils import (
    fmt_dt, is_valid_email, is_valid_phone, is_valid_postal_code,
    money, require_row,
)
from database import db_session
from gui_base import EntityPanel, PanelPage, load_choices
from products import PRODUCT_SELECT, _fetch_product, _resolve_reference


def _text(key, label, max_len, required=False, **options):
    return {"key": key, "label": label, "max_len": max_len,
            "required": required, **options}


def _current(current, key):
    return None if current is None else current.get(key)


def _email_field(current):
    return _text(
        "email", "Email", 150, wide=True, value=_current(current, "email"),
        validator=is_valid_email,
        error="Enter a valid email such as name@example.com."
    )


def _phone_field(current):
    return _text(
        "phone", "Phone", 30, value=_current(current, "phone"),
        validator=is_valid_phone,
        error="Use 7-30 digits, spaces, + - ( ) or ."
    )


def _postal_field(current):
    return _text(
        "postal_code", "Postal code", 20,
        value=_current(current, "postal_code"),
        validator=is_valid_postal_code,
        error="Use 3-20 letters, digits, spaces or dashes."
    )


def _address_fields(current):
    return [
        _text("street_address", "Street address", 200, wide=True,
              value=_current(current, "street_address")),
        _text("city", "City", 100, value=_current(current, "city")),
        _text("state", "State", 50, value=_current(current, "state")),
        _postal_field(current),
    ]


# --------------------------------------------------
# PRODUCTS
# --------------------------------------------------

class ProductsPanel(EntityPanel):
    singular = "product"
    table_name = "Products"
    id_column = "product_id"
    dependents = "inventory, sales, orders, reorders or shipments"
    form_columns = 2
    columns = [("ID", 60, "e"), ("Product", 260, "w", True),
               ("Brand", 150), ("Type", 150), ("Price", 90, "e")]
    list_sql = PRODUCT_SELECT + " ORDER BY p.product_id"

    def format_row(self, row):
        return (row[0], row[1], row[2], row[3], money(row[4]))

    def describe(self, row):
        return f"product “{row[1]}” (ID {row[0]})"

    def load_context(self, cursor):
        return load_choices(cursor, "brands", "types")

    def form_fields(self, current, context):
        return [
            {"key": "product_name", "label": "Product name", "wide": True,
             "max_len": 150, "value": _current(current, "product_name")},
            {"key": "brand_id", "label": "Brand", "kind": "choice",
             "choices": context.get("brands", []), "editable": True,
             "value": _current(current, "brand_id"),
             "hint": "Pick one, or type a new name to create it."},
            {"key": "product_type_id", "label": "Product type",
             "kind": "choice", "choices": context.get("types", []),
             "editable": True, "value": _current(current, "product_type_id"),
             "hint": "Pick one, or type a new name to create it."},
            {"key": "unit_price", "label": "Unit price ($)", "kind": "money",
             "value": _current(current, "unit_price")},
        ]

    def prepare(self, cursor, values):
        def choice(value):
            return ("id", value) if isinstance(value, int) else ("new", value)

        values["brand_id"] = _resolve_reference(
            cursor, "Brands", "brand_id", "brand_name",
            choice(values["brand_id"])
        )
        values["product_type_id"] = _resolve_reference(
            cursor, "Product_Types", "product_type_id", "type_name",
            choice(values["product_type_id"])
        )

        return values

    def load_details(self, row):
        product_id = int(row[0])

        with db_session() as cursor:
            product = _fetch_product(cursor, product_id)

            cursor.execute("""
                SELECT s.store_name, i.quantity
                FROM Inventory i
                JOIN Stores s ON i.store_id = s.store_id
                WHERE i.product_id = :product_id
                ORDER BY s.store_name
            """, {"product_id": product_id})
            stock = cursor.fetchall()

            cursor.execute("""
                SELECT NVL(SUM(quantity), 0),
                       NVL(SUM(quantity * unit_price), 0)
                FROM Sale_Items
                WHERE product_id = :product_id
            """, {"product_id": product_id})
            units_sold, revenue = cursor.fetchone()

            cursor.execute("""
                SELECT NVL(SUM(quantity), 0)
                FROM Web_Order_Items
                WHERE product_id = :product_id
            """, {"product_id": product_id})
            units_online = cursor.fetchone()[0]

        return {
            "title": product[1],
            "subtitle": f"{product[2]}  ·  {product[3]}",
            "fields": [
                ("Product ID", product[0]),
                ("Unit price", money(product[4])),
                ("Units sold in store", f"{units_sold:,}"),
                ("Store sales revenue", money(revenue)),
                ("Units on web orders", f"{units_online:,}"),
                ("Total in stock", f"{sum(r[1] for r in stock):,}"),
            ],
            "tables": [(
                "Stock by store", [("Store", 200, "w", True), ("Qty", 70, "e")],
                stock
            )],
        }


# --------------------------------------------------
# STORES
# --------------------------------------------------

class StoresPanel(EntityPanel):
    singular = "store"
    table_name = "Stores"
    id_column = "store_id"
    dependents = "inventory, sales or reorders"
    form_columns = 2
    columns = [("ID", 55, "e"), ("Name", 200, "w", True), ("Street", 200),
               ("City", 120), ("State", 70), ("Postal code", 100)]
    list_sql = """
        SELECT store_id, store_name, street_address, city, state, postal_code
        FROM Stores
        ORDER BY store_id
    """

    def describe(self, row):
        return f"store “{row[1]}” (ID {row[0]})"

    def form_fields(self, current, context):
        return [
            {"key": "store_name", "label": "Store name", "wide": True,
             "max_len": 150, "value": _current(current, "store_name")},
            *_address_fields(current),
        ]

    def load_details(self, row):
        store_id = int(row[0])
        params = {"store_id": store_id}

        with db_session() as cursor:
            store = require_row(
                cursor,
                "SELECT store_name, street_address, city, state, postal_code "
                "FROM Stores WHERE store_id = :store_id",
                params, f"Store {store_id} not found."
            )

            cursor.execute("""
                SELECT COUNT(*), NVL(SUM(quantity), 0)
                FROM Inventory WHERE store_id = :store_id
            """, params)
            lines, units = cursor.fetchone()

            cursor.execute("""
                SELECT COUNT(DISTINCT sa.sale_id),
                       NVL(SUM(si.quantity * si.unit_price), 0)
                FROM Sales sa
                LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
                WHERE sa.store_id = :store_id
            """, params)
            sales, revenue = cursor.fetchone()

            cursor.execute(
                "SELECT COUNT(*) FROM Reorders WHERE store_id = :store_id",
                params
            )
            reorders = cursor.fetchone()[0]

            cursor.execute("""
                SELECT * FROM (
                    SELECT p.product_name, i.quantity
                    FROM Inventory i
                    JOIN Products p ON i.product_id = p.product_id
                    WHERE i.store_id = :store_id
                    ORDER BY i.quantity, p.product_name
                ) WHERE ROWNUM <= 5
            """, params)
            lowest = cursor.fetchall()

        return {
            "title": store[0],
            "subtitle": ", ".join(part for part in store[1:] if part),
            "fields": [
                ("Store ID", store_id),
                ("Products stocked", lines),
                ("Units in stock", f"{units:,}"),
                ("Sales recorded", sales),
                ("Sales revenue", money(revenue)),
                ("Reorders placed", reorders),
            ],
            "tables": [(
                "Lowest stock", [("Product", 220, "w", True),
                                 ("Qty", 60, "e")], lowest
            )],
        }


# --------------------------------------------------
# CUSTOMERS
# --------------------------------------------------

class CustomersPanel(EntityPanel):
    singular = "customer"
    table_name = "Customers"
    id_column = "customer_id"
    dependents = "sales or web orders"
    form_columns = 2
    columns = [("ID", 55, "e"), ("First", 110), ("Last", 120),
               ("Email", 220, "w", True), ("Phone", 130), ("City", 110),
               ("State", 60)]
    list_sql = """
        SELECT customer_id, first_name, last_name, email, phone, city, state
        FROM Customers
        ORDER BY customer_id
    """

    def describe(self, row):
        return f"customer {row[1]} {row[2]} (ID {row[0]})"

    def form_fields(self, current, context):
        return [
            _text("first_name", "First name", 100, required=True,
                  value=_current(current, "first_name")),
            _text("last_name", "Last name", 100, required=True,
                  value=_current(current, "last_name")),
            _email_field(current),
            _phone_field(current),
            *_address_fields(current),
        ]

    def load_details(self, row):
        customer_id = int(row[0])
        params = {"id": customer_id}

        with db_session() as cursor:
            customer = require_row(
                cursor,
                """
                SELECT first_name, last_name, email, phone,
                       street_address, city, state, postal_code
                FROM Customers WHERE customer_id = :id
                """,
                params, f"Customer {customer_id} not found."
            )

            cursor.execute("""
                SELECT sa.sale_id, sa.sale_date,
                       NVL(SUM(si.quantity * si.unit_price), 0)
                FROM Sales sa
                LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
                WHERE sa.customer_id = :id
                GROUP BY sa.sale_id, sa.sale_date
                ORDER BY sa.sale_date DESC
            """, params)
            sales = cursor.fetchall()

            cursor.execute("""
                SELECT wo.order_id, wo.order_date, wo.order_status,
                       NVL(SUM(woi.quantity * woi.unit_price), 0)
                FROM Web_Orders wo
                LEFT JOIN Web_Order_Items woi ON wo.order_id = woi.order_id
                WHERE wo.customer_id = :id
                GROUP BY wo.order_id, wo.order_date, wo.order_status
                ORDER BY wo.order_date DESC
            """, params)
            orders = cursor.fetchall()

        return {
            "title": f"{customer[0]} {customer[1]}",
            "subtitle": customer[2],
            "fields": [
                ("Customer ID", customer_id),
                ("Phone", customer[3]),
                ("Address", ", ".join(p for p in customer[4:] if p)),
                ("Store purchases",
                 f"{len(sales)} · {money(sum(r[2] for r in sales))}"),
                ("Online orders",
                 f"{len(orders)} · {money(sum(r[3] for r in orders))}"),
            ],
            "tables": [
                ("Store purchases",
                 [("Sale", 45, "e"), ("Date", 130, "w", True),
                  ("Total", 90, "e")],
                 [(r[0], fmt_dt(r[1]), money(r[2])) for r in sales]),
                ("Online orders",
                 [("Order", 50, "e"), ("Date", 105, "w", True),
                  ("Status", 80), ("Total", 75, "e")],
                 [(r[0], fmt_dt(r[1]), r[2], money(r[3])) for r in orders]),
            ],
        }


# --------------------------------------------------
# VENDORS
# --------------------------------------------------

class VendorsPanel(EntityPanel):
    singular = "vendor"
    table_name = "Vendors"
    id_column = "vendor_id"
    dependents = "reorder records"
    form_columns = 2
    columns = [("ID", 55, "e"), ("Name", 220, "w", True), ("Phone", 130),
               ("Email", 220), ("City", 110), ("State", 60)]
    list_sql = """
        SELECT vendor_id, vendor_name, phone, email, city, state
        FROM Vendors
        ORDER BY vendor_id
    """

    def describe(self, row):
        return f"vendor “{row[1]}” (ID {row[0]})"

    def form_fields(self, current, context):
        return [
            {"key": "vendor_name", "label": "Vendor name", "wide": True,
             "max_len": 150, "value": _current(current, "vendor_name")},
            _phone_field(current),
            _email_field(current) | {"wide": False},
            *_address_fields(current),
        ]

    def load_details(self, row):
        vendor_id = int(row[0])
        params = {"id": vendor_id}

        with db_session() as cursor:
            vendor = require_row(
                cursor,
                """
                SELECT vendor_name, phone, email,
                       street_address, city, state, postal_code
                FROM Vendors WHERE vendor_id = :id
                """,
                params, f"Vendor {vendor_id} not found."
            )

            cursor.execute("""
                SELECT r.reorder_id, s.store_name, r.reorder_status,
                       NVL(SUM(ri.quantity), 0)
                FROM Reorders r
                JOIN Stores s ON r.store_id = s.store_id
                LEFT JOIN Reorder_Items ri ON r.reorder_id = ri.reorder_id
                WHERE r.vendor_id = :id
                GROUP BY r.reorder_id, s.store_name, r.reorder_status,
                         r.reorder_date
                ORDER BY r.reorder_date DESC
            """, params)
            reorders = cursor.fetchall()

        return {
            "title": vendor[0],
            "subtitle": vendor[2],
            "fields": [
                ("Vendor ID", vendor_id),
                ("Phone", vendor[1]),
                ("Address", ", ".join(p for p in vendor[3:] if p)),
                ("Reorders", len(reorders)),
            ],
            "tables": [(
                "Reorders",
                [("ID", 40, "e"), ("Store", 130, "w", True),
                 ("Status", 90), ("Units", 50, "e")],
                reorders
            )],
        }


# --------------------------------------------------
# PAGES
# --------------------------------------------------

class ProductsPage(PanelPage):
    title = "Products"
    subtitle = "Everything you sell, with brand, type and price."
    panel_class = ProductsPanel


class StoresPage(PanelPage):
    title = "Stores"
    subtitle = "Your store locations and how each one is doing."
    panel_class = StoresPanel


class CustomersPage(PanelPage):
    title = "Customers"
    subtitle = "Registered customers and their purchase history."
    panel_class = CustomersPanel


class VendorsPage(PanelPage):
    title = "Vendors"
    subtitle = "Suppliers you reorder stock from."
    panel_class = VendorsPanel
