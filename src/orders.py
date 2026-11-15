from database import db_session
from cli_utils import (
    UserError, confirm, fmt_dt, money, print_record, print_table,
    prompt_int, prompt_text, require_row, run_menu,
)

MAX_ITEM_QUANTITY = 1_000_000

# Allowed status changes. Terminal statuses (Delivered / Cancelled /
# Received) cannot be changed again. These match the CHECK constraints in
# 02_create_constraints.sql.
ORDER_TRANSITIONS = {
    "Pending": ["Processing", "Cancelled"],
    "Processing": ["Shipped", "Cancelled"],
    "Shipped": ["Delivered"],
    "Delivered": [],
    "Cancelled": [],
}

REORDER_TRANSITIONS = {
    "Pending": ["Ordered", "Cancelled"],
    "Ordered": ["Partially Received", "Received", "Cancelled"],
    "Partially Received": ["Received", "Cancelled"],
    "Received": [],
    "Cancelled": [],
}


# --------------------------------------------------
# SHARED HELPERS
# --------------------------------------------------

def _collect_lines(with_price):
    """
    Ask for products and quantities until the user is done.

    Returns {product_id: [name, unit_price, quantity]}; the same product
    entered twice is merged into one line.
    """

    lines = {}

    while True:
        product_id = prompt_int("\nProduct ID", minimum=1)
        quantity = prompt_int(
            "Quantity", minimum=1, maximum=MAX_ITEM_QUANTITY
        )

        with db_session() as cursor:
            name, price = require_row(
                cursor,
                "SELECT product_name, unit_price FROM Products "
                "WHERE product_id = :id",
                {"id": product_id}, f"Product {product_id} not found."
            )

        if product_id in lines:
            lines[product_id][2] += quantity
        else:
            lines[product_id] = [name, price, quantity]

        shown = f" at {money(price)}" if with_price else ""
        print(f"Added {quantity} x {name}{shown}.")

        if not confirm("Add another product"):
            return lines


def _choose_status(current, transitions):
    """Let the user pick a new status from the allowed transitions."""

    allowed = transitions[current]

    if not allowed:
        raise UserError(
            f"Status '{current}' is final and cannot be changed."
        )

    print(f"\nCurrent status: {current}")
    print("Allowed new statuses:")

    for number, status in enumerate(allowed, start=1):
        print(f"{number}. {status}")

    choice = prompt_int("Select new status", minimum=1, maximum=len(allowed))

    return allowed[choice - 1]


# --------------------------------------------------
# ONLINE (WEB) ORDERS
# --------------------------------------------------

def create_order():
    """Create a new online order with one or more products."""

    print("\n--- Create Online Order (type 'cancel' to stop) ---")

    customer_id = prompt_int("Enter customer ID", minimum=1)

    with db_session() as cursor:
        first, last = require_row(
            cursor,
            "SELECT first_name, last_name FROM Customers "
            "WHERE customer_id = :id",
            {"id": customer_id}, f"Customer {customer_id} not found."
        )

    print(f"Customer: {first} {last}")

    lines = _collect_lines(with_price=True)
    total = sum(price * qty for _, price, qty in lines.values())

    print("\nOrder summary:")
    print_table(
        ["Product", "Qty", "Price", "Subtotal"],
        [(n, q, money(p), money(p * q)) for n, p, q in lines.values()]
    )
    print(f"Total: {money(total)}")

    if not confirm("Place this order"):
        raise UserError("Order not placed.")

    with db_session() as cursor:
        order_id = cursor.var(int)
        cursor.execute("""
            INSERT INTO Web_Orders (customer_id, order_status)
            VALUES (:customer_id, 'Pending')
            RETURNING order_id INTO :order_id
        """, {"customer_id": customer_id, "order_id": order_id})
        new_order_id = order_id.getvalue()[0]

        for product_id, (_, price, quantity) in lines.items():
            cursor.execute("""
                INSERT INTO Web_Order_Items (
                    order_id, product_id, quantity, unit_price
                )
                VALUES (:order_id, :product_id, :quantity, :unit_price)
            """, {
                "order_id": new_order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": price
            })

    print(f"Order created successfully! Order ID: {new_order_id}  "
          f"Total: {money(total)}")


def view_orders():
    """Display all online orders with their totals."""

    print("\n--- Online Orders ---")

    status = None
    choice = prompt_text(
        "Filter by status (Pending/Processing/Shipped/Delivered/Cancelled, "
        "Enter for all)", required=False
    )

    if choice:
        matches = [s for s in ORDER_TRANSITIONS if s.lower() == choice.lower()]

        if not matches:
            raise UserError(f"'{choice}' is not a valid order status.")

        status = matches[0]

    with db_session() as cursor:
        cursor.execute("""
            SELECT wo.order_id,
                   wo.order_date,
                   c.first_name || ' ' || c.last_name,
                   wo.order_status,
                   NVL(SUM(woi.quantity), 0),
                   NVL(SUM(woi.quantity * woi.unit_price), 0)
            FROM Web_Orders wo
            JOIN Customers c ON wo.customer_id = c.customer_id
            LEFT JOIN Web_Order_Items woi ON wo.order_id = woi.order_id
            WHERE :status IS NULL OR wo.order_status = :status
            GROUP BY wo.order_id, wo.order_date, c.first_name, c.last_name,
                     wo.order_status
            ORDER BY wo.order_date DESC, wo.order_id DESC
        """, {"status": status})
        rows = cursor.fetchall()

    if not rows:
        print("No orders found.")
        return

    print_table(
        ["Order ID", "Date", "Customer", "Status", "Units", "Total"],
        [(r[0], fmt_dt(r[1]), r[2], r[3], r[4], money(r[5])) for r in rows]
    )


def view_order_details():
    """Display one online order and its products."""

    print("\n--- Order Details ---")

    order_id = prompt_int("Enter order ID", minimum=1)

    with db_session() as cursor:
        order = require_row(
            cursor,
            """
            SELECT wo.order_id, wo.order_date, wo.order_status,
                   wo.customer_id, c.first_name || ' ' || c.last_name
            FROM Web_Orders wo
            JOIN Customers c ON wo.customer_id = c.customer_id
            WHERE wo.order_id = :id
            """,
            {"id": order_id}, f"Order {order_id} not found."
        )

        cursor.execute("""
            SELECT oi.product_id,
                   p.product_name,
                   oi.quantity,
                   oi.unit_price,
                   oi.quantity * oi.unit_price
            FROM Web_Order_Items oi
            JOIN Products p ON oi.product_id = p.product_id
            WHERE oi.order_id = :id
            ORDER BY p.product_name
        """, {"id": order_id})
        items = cursor.fetchall()

    print()
    print_record([
        ("Order ID", order[0]),
        ("Date", fmt_dt(order[1])),
        ("Status", order[2]),
        ("Customer", f"{order[4]} (ID {order[3]})"),
    ])

    if not items:
        print("\nThis order has no products yet.")
        return

    print()
    print_table(
        ["Product ID", "Product", "Qty", "Unit price", "Subtotal"],
        [(r[0], r[1], r[2], money(r[3]), money(r[4])) for r in items]
    )
    print(f"Order total: {money(sum(r[4] for r in items))}")


def add_order_item():
    """Add a product to a pending online order."""

    print("\n--- Add Product to Order (type 'cancel' to stop) ---")

    order_id = prompt_int("Enter order ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)
    quantity = prompt_int(
        "Enter quantity", minimum=1, maximum=MAX_ITEM_QUANTITY
    )

    with db_session() as cursor:
        status = require_row(
            cursor,
            "SELECT order_status FROM Web_Orders WHERE order_id = :id "
            "FOR UPDATE",
            {"id": order_id}, f"Order {order_id} not found."
        )[0]

        if status != "Pending":
            raise UserError("Products can only be added to pending orders.")

        price = require_row(
            cursor,
            "SELECT unit_price FROM Products WHERE product_id = :id",
            {"id": product_id}, f"Product {product_id} not found."
        )[0]

        cursor.execute("""
            UPDATE Web_Order_Items
            SET quantity = quantity + :quantity
            WHERE order_id = :order_id AND product_id = :product_id
        """, {
            "quantity": quantity,
            "order_id": order_id,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO Web_Order_Items (
                    order_id, product_id, quantity, unit_price
                )
                VALUES (:order_id, :product_id, :quantity, :unit_price)
            """, {
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": price
            })

    print("Product added to order successfully!")


def update_order_status():
    """Move an online order to its next status."""

    print("\n--- Update Order Status ---")

    order_id = prompt_int("Enter order ID", minimum=1)

    with db_session() as cursor:
        current = require_row(
            cursor,
            "SELECT order_status FROM Web_Orders WHERE order_id = :id",
            {"id": order_id}, f"Order {order_id} not found."
        )[0]

    new_status = _choose_status(current, ORDER_TRANSITIONS)

    with db_session() as cursor:
        # Re-check the old status so two users cannot both change it.
        cursor.execute("""
            UPDATE Web_Orders
            SET order_status = :new_status
            WHERE order_id = :order_id AND order_status = :old_status
        """, {
            "new_status": new_status,
            "order_id": order_id,
            "old_status": current
        })

        if cursor.rowcount == 0:
            raise UserError(
                "The order was changed by someone else. Please try again."
            )

    print(f"Order {order_id} is now {new_status}.")


def delete_order():
    """Delete an online order and its items."""

    print("\n--- Delete Online Order ---")

    order_id = prompt_int("Enter order ID", minimum=1)

    if not confirm(f"Delete order {order_id} and its items"):
        print("Delete cancelled.")
        return

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
            "DELETE FROM Web_Orders WHERE order_id = :id", {"id": order_id}
        )

    print(f"Order {order_id} deleted.")


# --------------------------------------------------
# VENDOR REORDERS
# --------------------------------------------------

def create_reorder():
    """Order stock for a store from a vendor."""

    print("\n--- Create Vendor Reorder (type 'cancel' to stop) ---")

    vendor_id = prompt_int("Enter vendor ID", minimum=1)
    store_id = prompt_int("Enter store ID", minimum=1)

    with db_session() as cursor:
        vendor = require_row(
            cursor, "SELECT vendor_name FROM Vendors WHERE vendor_id = :id",
            {"id": vendor_id}, f"Vendor {vendor_id} not found."
        )[0]
        store = require_row(
            cursor, "SELECT store_name FROM Stores WHERE store_id = :id",
            {"id": store_id}, f"Store {store_id} not found."
        )[0]

    print(f"Vendor: {vendor}  ->  Store: {store}")

    lines = _collect_lines(with_price=False)

    if not confirm("Place this reorder"):
        raise UserError("Reorder not placed.")

    with db_session() as cursor:
        reorder_id = cursor.var(int)
        cursor.execute("""
            INSERT INTO Reorders (vendor_id, store_id, reorder_status)
            VALUES (:vendor_id, :store_id, 'Pending')
            RETURNING reorder_id INTO :reorder_id
        """, {
            "vendor_id": vendor_id,
            "store_id": store_id,
            "reorder_id": reorder_id
        })
        new_id = reorder_id.getvalue()[0]

        for product_id, (_, _, quantity) in lines.items():
            cursor.execute("""
                INSERT INTO Reorder_Items (reorder_id, product_id, quantity)
                VALUES (:reorder_id, :product_id, :quantity)
            """, {
                "reorder_id": new_id,
                "product_id": product_id,
                "quantity": quantity
            })

    print(f"Reorder created successfully! Reorder ID: {new_id}")


def view_reorders():
    """Display all vendor reorders."""

    print("\n--- Vendor Reorders ---")

    with db_session() as cursor:
        cursor.execute("""
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
            GROUP BY r.reorder_id, r.reorder_date, v.vendor_name,
                     s.store_name, r.reorder_status
            ORDER BY r.reorder_date DESC, r.reorder_id DESC
        """)
        rows = cursor.fetchall()

    if not rows:
        print("No reorders found.")
        return

    print_table(
        ["Reorder ID", "Date", "Vendor", "Store", "Status", "Units"],
        [(r[0], fmt_dt(r[1]), r[2], r[3], r[4], r[5]) for r in rows]
    )


def view_reorder_details():
    """Display one reorder, its products, and any shipments."""

    print("\n--- Reorder Details ---")

    reorder_id = prompt_int("Enter reorder ID", minimum=1)

    with db_session() as cursor:
        reorder = require_row(
            cursor,
            """
            SELECT r.reorder_id, r.reorder_date, r.reorder_status,
                   v.vendor_name, s.store_name
            FROM Reorders r
            JOIN Vendors v ON r.vendor_id = v.vendor_id
            JOIN Stores s ON r.store_id = s.store_id
            WHERE r.reorder_id = :id
            """,
            {"id": reorder_id}, f"Reorder {reorder_id} not found."
        )

        cursor.execute("""
            SELECT ri.product_id, p.product_name, ri.quantity
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
            LEFT JOIN Shipment_Items shi ON sh.shipment_id = shi.shipment_id
            WHERE sh.reorder_id = :id
            GROUP BY sh.shipment_id, sh.shipment_status, sh.shipment_date
            ORDER BY sh.shipment_id
        """, {"id": reorder_id})
        shipments = cursor.fetchall()

    print()
    print_record([
        ("Reorder ID", reorder[0]),
        ("Date", fmt_dt(reorder[1])),
        ("Status", reorder[2]),
        ("Vendor", reorder[3]),
        ("Store", reorder[4]),
    ])

    print("\nProducts ordered:")
    print_table(["Product ID", "Product", "Quantity"], items)

    if shipments:
        print("\nShipments:")
        print_table(
            ["Shipment ID", "Status", "Date", "Units"],
            [(r[0], r[1], fmt_dt(r[2]), r[3]) for r in shipments]
        )


def update_reorder_status():
    """Move a vendor reorder to its next status."""

    print("\n--- Update Reorder Status ---")

    reorder_id = prompt_int("Enter reorder ID", minimum=1)

    with db_session() as cursor:
        current = require_row(
            cursor,
            "SELECT reorder_status FROM Reorders WHERE reorder_id = :id",
            {"id": reorder_id}, f"Reorder {reorder_id} not found."
        )[0]

    new_status = _choose_status(current, REORDER_TRANSITIONS)

    with db_session() as cursor:
        cursor.execute("""
            UPDATE Reorders
            SET reorder_status = :new_status
            WHERE reorder_id = :reorder_id AND reorder_status = :old_status
        """, {
            "new_status": new_status,
            "reorder_id": reorder_id,
            "old_status": current
        })

        if cursor.rowcount == 0:
            raise UserError(
                "The reorder was changed by someone else. Please try again."
            )

    print(f"Reorder {reorder_id} is now {new_status}.")


def orders_menu():
    """Display the order management menu."""

    run_menu("Order Management", [
        ("Create Online Order", create_order),
        ("View Online Orders", view_orders),
        ("View Online Order Details", view_order_details),
        ("Add Product to Online Order", add_order_item),
        ("Update Online Order Status", update_order_status),
        ("Delete Online Order", delete_order),
        ("Create Vendor Reorder", create_reorder),
        ("View Vendor Reorders", view_reorders),
        ("View Vendor Reorder Details", view_reorder_details),
        ("Update Vendor Reorder Status", update_reorder_status),
    ])


if __name__ == "__main__":
    orders_menu()
