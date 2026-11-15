from database import db_session
from cli_utils import (
    UserError, confirm, fmt_dt, money, print_record, print_table,
    prompt_int, require_row, run_menu,
)

MAX_ITEM_QUANTITY = 1_000_000


# --------------------------------------------------
# SHARED TRANSACTION STEPS
# --------------------------------------------------

def _sell_item(cursor, sale_id, store_id, product_id, quantity):
    """
    Add a product to a sale and take it out of the store's inventory.

    Must be called inside a db_session(). The inventory row is locked
    (FOR UPDATE) so two cashiers cannot sell the same last unit, and any
    UserError rolls back the whole sale.
    """

    _, price = require_row(
        cursor,
        "SELECT product_id, unit_price FROM Products WHERE product_id = :id",
        {"id": product_id}, f"Product {product_id} not found."
    )

    row = require_row(
        cursor,
        """
        SELECT quantity
        FROM Inventory
        WHERE store_id = :store_id AND product_id = :product_id
        FOR UPDATE
        """,
        {"store_id": store_id, "product_id": product_id},
        f"Product {product_id} is not stocked at store {store_id}."
    )

    if row[0] < quantity:
        raise UserError(
            f"Insufficient stock for product {product_id}: "
            f"{row[0]} available, {quantity} requested."
        )

    # Selling the same product twice on one sale merges into one line,
    # because (sale_id, product_id) is the primary key of Sale_Items.
    cursor.execute("""
        UPDATE Sale_Items
        SET quantity = quantity + :quantity
        WHERE sale_id = :sale_id AND product_id = :product_id
    """, {
        "quantity": quantity, "sale_id": sale_id, "product_id": product_id
    })

    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO Sale_Items (sale_id, product_id, quantity, unit_price)
            VALUES (:sale_id, :product_id, :quantity, :unit_price)
        """, {
            "sale_id": sale_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": price
        })

    cursor.execute("""
        UPDATE Inventory
        SET quantity = quantity - :quantity
        WHERE store_id = :store_id AND product_id = :product_id
    """, {
        "quantity": quantity, "store_id": store_id, "product_id": product_id
    })

    return price


def _prompt_store_and_customer():
    """Ask for a store and an optional customer, and verify both exist."""

    store_id = prompt_int("Enter store ID", minimum=1)
    customer_id = prompt_int(
        "Enter customer ID (leave blank for anonymous sale)",
        minimum=1, required=False
    )

    with db_session() as cursor:
        store = require_row(
            cursor, "SELECT store_name FROM Stores WHERE store_id = :id",
            {"id": store_id}, f"Store {store_id} not found."
        )[0]

        customer = None

        if customer_id is not None:
            first, last = require_row(
                cursor,
                "SELECT first_name, last_name FROM Customers "
                "WHERE customer_id = :id",
                {"id": customer_id}, f"Customer {customer_id} not found."
            )
            customer = f"{first} {last}"

    return store_id, store, customer_id, customer


# --------------------------------------------------
# RECORD A SALE
# --------------------------------------------------

def record_sale():
    """Record a complete sale with one or more products in one transaction."""

    print("\n--- Record Sale (type 'cancel' to stop) ---")

    store_id, store_name, customer_id, customer_name = (
        _prompt_store_and_customer()
    )

    print(f"\nStore: {store_name}")
    print(f"Customer: {customer_name or 'Anonymous'}")

    cart = {}   # product_id -> [name, price, quantity]

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
            stock = require_row(
                cursor,
                "SELECT quantity FROM Inventory "
                "WHERE store_id = :store_id AND product_id = :product_id",
                {"store_id": store_id, "product_id": product_id},
                f"{name} is not stocked at {store_name}."
            )[0]

        wanted = quantity + (cart[product_id][2] if product_id in cart else 0)

        if wanted > stock:
            print(
                f"Not enough stock for {name}: {stock} available, "
                f"{wanted} requested. Item not added."
            )
        else:
            cart[product_id] = [name, price, wanted]
            print(f"Added {quantity} x {name} at {money(price)}.")

        if not confirm("Add another product"):
            break

    if not cart:
        raise UserError("No products were added. Sale not recorded.")

    total = sum(price * qty for _, price, qty in cart.values())

    print("\nSale summary:")
    print_table(
        ["Product", "Qty", "Price", "Subtotal"],
        [(n, q, money(p), money(p * q)) for n, p, q in cart.values()]
    )
    print(f"Total: {money(total)}")

    if not confirm("Complete this sale"):
        raise UserError("Sale not recorded.")

    # All-or-nothing: sale header, all items, and all stock changes.
    with db_session() as cursor:
        sale_id = cursor.var(int)
        cursor.execute("""
            INSERT INTO Sales (store_id, customer_id)
            VALUES (:store_id, :customer_id)
            RETURNING sale_id INTO :sale_id
        """, {
            "store_id": store_id,
            "customer_id": customer_id,
            "sale_id": sale_id
        })
        new_sale_id = sale_id.getvalue()[0]

        for product_id, (_, _, quantity) in cart.items():
            _sell_item(cursor, new_sale_id, store_id, product_id, quantity)

    print(f"Sale recorded successfully! Sale ID: {new_sale_id}  "
          f"Total: {money(total)}")


def create_sale():
    """Create an empty sale, to which products can be added later."""

    print("\n--- Create Sale (type 'cancel' to stop) ---")

    store_id, _, customer_id, _ = _prompt_store_and_customer()

    with db_session() as cursor:
        sale_id = cursor.var(int)
        cursor.execute("""
            INSERT INTO Sales (store_id, customer_id)
            VALUES (:store_id, :customer_id)
            RETURNING sale_id INTO :sale_id
        """, {
            "store_id": store_id,
            "customer_id": customer_id,
            "sale_id": sale_id
        })

    print(f"Sale created successfully! Sale ID: {sale_id.getvalue()[0]}")


def add_sale_item():
    """Add a product to an existing sale and update inventory."""

    print("\n--- Add Product to Sale (type 'cancel' to stop) ---")

    sale_id = prompt_int("Enter sale ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)
    quantity = prompt_int("Enter quantity", minimum=1,
                          maximum=MAX_ITEM_QUANTITY)

    with db_session() as cursor:
        store_id = require_row(
            cursor, "SELECT store_id FROM Sales WHERE sale_id = :id",
            {"id": sale_id}, f"Sale {sale_id} not found."
        )[0]

        _sell_item(cursor, sale_id, store_id, product_id, quantity)

        cursor.execute("""
            SELECT quantity FROM Inventory
            WHERE store_id = :store_id AND product_id = :product_id
        """, {"store_id": store_id, "product_id": product_id})
        remaining = cursor.fetchone()[0]

    print("Product added to sale successfully!")
    print(f"Inventory remaining at store {store_id}: {remaining}")


# --------------------------------------------------
# RETRIEVE SALES
# --------------------------------------------------

SALES_LIST_SQL = """
    SELECT sa.sale_id,
           sa.sale_date,
           st.store_name,
           NVL2(c.customer_id, c.first_name || ' ' || c.last_name, NULL),
           NVL(SUM(si.quantity), 0),
           NVL(SUM(si.quantity * si.unit_price), 0)
    FROM Sales sa
    JOIN Stores st ON sa.store_id = st.store_id
    LEFT JOIN Customers c ON sa.customer_id = c.customer_id
    LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
    {where}
    GROUP BY sa.sale_id, sa.sale_date, st.store_name,
             c.customer_id, c.first_name, c.last_name
    ORDER BY sa.sale_date DESC, sa.sale_id DESC
"""

SALES_HEADERS = ["Sale ID", "Date", "Store", "Customer", "Units", "Total"]


def _print_sales(rows, empty_message):
    if not rows:
        print(empty_message)
        return

    print_table(
        SALES_HEADERS,
        [(r[0], fmt_dt(r[1]), r[2], r[3] or "Anonymous", r[4], money(r[5]))
         for r in rows]
    )
    print(f"Combined total: {money(sum(r[5] for r in rows))}")


def view_sales():
    """Display all sales."""

    with db_session() as cursor:
        cursor.execute(SALES_LIST_SQL.format(where=""))
        rows = cursor.fetchall()

    print("\n--- Sales Transactions ---")
    _print_sales(rows, "No sales found.")


def view_sale_details():
    """Display one sale and the products in it."""

    print("\n--- Sale Details ---")

    sale_id = prompt_int("Enter sale ID", minimum=1)

    with db_session() as cursor:
        sale = require_row(
            cursor,
            """
            SELECT sa.sale_id, sa.sale_date, st.store_name,
                   NVL2(c.customer_id, c.first_name || ' ' || c.last_name, NULL)
            FROM Sales sa
            JOIN Stores st ON sa.store_id = st.store_id
            LEFT JOIN Customers c ON sa.customer_id = c.customer_id
            WHERE sa.sale_id = :id
            """,
            {"id": sale_id}, f"Sale {sale_id} not found."
        )

        cursor.execute("""
            SELECT si.product_id,
                   p.product_name,
                   si.quantity,
                   si.unit_price,
                   si.quantity * si.unit_price
            FROM Sale_Items si
            JOIN Products p ON si.product_id = p.product_id
            WHERE si.sale_id = :id
            ORDER BY p.product_name
        """, {"id": sale_id})
        items = cursor.fetchall()

    print()
    print_record([
        ("Sale ID", sale[0]),
        ("Date", fmt_dt(sale[1])),
        ("Store", sale[2]),
        ("Customer", sale[3] or "Anonymous"),
    ])

    if not items:
        print("\nThis sale has no products yet.")
        return

    print()
    print_table(
        ["Product ID", "Product", "Qty", "Unit price", "Subtotal"],
        [(r[0], r[1], r[2], money(r[3]), money(r[4])) for r in items]
    )
    print(f"Sale total: {money(sum(r[4] for r in items))}")


def search_sales_by_store():
    """Find sales made at a particular store."""

    print("\n--- Search Sales by Store ---")

    store_id = prompt_int("Enter store ID", minimum=1)

    with db_session() as cursor:
        require_row(
            cursor, "SELECT 1 FROM Stores WHERE store_id = :id",
            {"id": store_id}, f"Store {store_id} not found."
        )
        cursor.execute(
            SALES_LIST_SQL.format(where="WHERE sa.store_id = :store_id"),
            {"store_id": store_id}
        )
        rows = cursor.fetchall()

    _print_sales(rows, "No sales found for this store.")


def search_sales_by_customer():
    """Find sales made by a particular customer."""

    print("\n--- Search Sales by Customer ---")

    customer_id = prompt_int("Enter customer ID", minimum=1)

    with db_session() as cursor:
        require_row(
            cursor, "SELECT 1 FROM Customers WHERE customer_id = :id",
            {"id": customer_id}, f"Customer {customer_id} not found."
        )
        cursor.execute(
            SALES_LIST_SQL.format(
                where="WHERE sa.customer_id = :customer_id"
            ),
            {"customer_id": customer_id}
        )
        rows = cursor.fetchall()

    _print_sales(rows, "No sales found for this customer.")


# --------------------------------------------------
# VOID A SALE
# --------------------------------------------------

def void_sale():
    """Delete a sale and return its products to the store's inventory."""

    print("\n--- Void Sale ---")

    sale_id = prompt_int("Enter sale ID", minimum=1)

    if not confirm(f"Void sale {sale_id} and restore its stock"):
        print("Void cancelled.")
        return

    with db_session() as cursor:
        store_id = require_row(
            cursor, "SELECT store_id FROM Sales WHERE sale_id = :id",
            {"id": sale_id}, f"Sale {sale_id} not found."
        )[0]

        cursor.execute(
            "SELECT product_id, quantity FROM Sale_Items WHERE sale_id = :id",
            {"id": sale_id}
        )
        items = cursor.fetchall()

        for product_id, quantity in items:
            # MERGE restores stock even if the inventory row was deleted.
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
            """, {
                "store_id": store_id,
                "product_id": product_id,
                "quantity": quantity
            })

        cursor.execute(
            "DELETE FROM Sale_Items WHERE sale_id = :id", {"id": sale_id}
        )
        cursor.execute(
            "DELETE FROM Sales WHERE sale_id = :id", {"id": sale_id}
        )

    print(f"Sale {sale_id} voided. Restored {len(items)} product line(s) "
          f"to inventory.")


def sales_menu():
    """Display the sales management menu."""

    run_menu("Sales Management", [
        ("Record Sale (multiple products)", record_sale),
        ("Create Empty Sale", create_sale),
        ("Add Product to Existing Sale", add_sale_item),
        ("View All Sales", view_sales),
        ("View Sale Details", view_sale_details),
        ("Search Sales by Store", search_sales_by_store),
        ("Search Sales by Customer", search_sales_by_customer),
        ("Void Sale", void_sale),
    ])


if __name__ == "__main__":
    sales_menu()
