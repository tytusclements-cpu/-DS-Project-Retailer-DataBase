from database import db_session
from cli_utils import (
    UserError, confirm, like_pattern, print_table, prompt_int, prompt_text,
    require_row, run_menu,
)

# NUMBER(10) in the schema
MAX_QUANTITY = 9_999_999_999

INVENTORY_HEADERS = ["Store ID", "Store", "Product ID", "Product", "Quantity"]


def _store_name(cursor, store_id):
    return require_row(
        cursor, "SELECT store_name FROM Stores WHERE store_id = :id",
        {"id": store_id}, f"Store {store_id} not found."
    )[0]


def _product_name(cursor, product_id):
    return require_row(
        cursor, "SELECT product_name FROM Products WHERE product_id = :id",
        {"id": product_id}, f"Product {product_id} not found."
    )[0]


def _print_inventory(rows, empty_message):
    if not rows:
        print(empty_message)
        return

    print_table(INVENTORY_HEADERS, rows)


INVENTORY_SELECT = """
    SELECT i.store_id,
           s.store_name,
           i.product_id,
           p.product_name,
           i.quantity
    FROM Inventory i
    JOIN Stores s ON i.store_id = s.store_id
    JOIN Products p ON i.product_id = p.product_id
"""


def view_inventory():
    """Display inventory for all stores."""

    with db_session() as cursor:
        cursor.execute(INVENTORY_SELECT + " ORDER BY s.store_name, p.product_name")
        rows = cursor.fetchall()

    print("\n--- Inventory List ---")
    _print_inventory(rows, "No inventory records found.")


def view_inventory_by_store():
    """Display inventory for a single store."""

    print("\n--- Inventory by Store ---")

    store_id = prompt_int("Enter store ID", minimum=1)

    with db_session() as cursor:
        name = _store_name(cursor, store_id)

        cursor.execute(
            INVENTORY_SELECT +
            " WHERE i.store_id = :store_id ORDER BY p.product_name",
            {"store_id": store_id}
        )
        rows = cursor.fetchall()

    print(f"\nInventory for {name}:")
    _print_inventory(rows, "This store has no inventory records.")


def search_inventory():
    """Search inventory by store ID or product name."""

    print("\n--- Search Inventory ---")

    term = prompt_text("Enter store ID or product name")

    with db_session() as cursor:
        cursor.execute(INVENTORY_SELECT + """
            WHERE TO_CHAR(i.store_id) = :search
               OR LOWER(p.product_name) LIKE LOWER(:product_search) ESCAPE '\\'
            ORDER BY s.store_name, p.product_name
        """, {"search": term, "product_search": like_pattern(term)})
        rows = cursor.fetchall()

    _print_inventory(rows, "No matching inventory records found.")


def check_availability():
    """Show where a product is in stock and how many units exist in total."""

    print("\n--- Check Product Availability ---")

    term = prompt_text("Enter product ID or product name")

    with db_session() as cursor:
        cursor.execute("""
            SELECT p.product_id,
                   p.product_name,
                   s.store_id,
                   s.store_name,
                   i.quantity
            FROM Products p
            LEFT JOIN Inventory i ON p.product_id = i.product_id
            LEFT JOIN Stores s ON i.store_id = s.store_id
            WHERE TO_CHAR(p.product_id) = :search
               OR LOWER(p.product_name) LIKE LOWER(:name_search) ESCAPE '\\'
            ORDER BY p.product_name, s.store_name
        """, {"search": term, "name_search": like_pattern(term)})
        rows = cursor.fetchall()

    if not rows:
        print("No matching products found.")
        return

    totals = {}

    for product_id, product_name, _, _, quantity in rows:
        entry = totals.setdefault(product_id, [product_name, 0])
        entry[1] += quantity or 0

    print_table(
        ["Product ID", "Product", "Store ID", "Store", "Quantity"], rows
    )

    print()

    for product_id, (product_name, total) in totals.items():
        status = "IN STOCK" if total > 0 else "OUT OF STOCK"
        print(f"{product_name} (ID {product_id}): {total} units total - {status}")


def low_stock():
    """List inventory records at or below a quantity threshold."""

    print("\n--- Low Stock Report ---")

    threshold = prompt_int(
        "Show items with quantity at or below", minimum=0,
        maximum=MAX_QUANTITY, default=20
    )

    with db_session() as cursor:
        cursor.execute(
            INVENTORY_SELECT +
            " WHERE i.quantity <= :threshold "
            "ORDER BY i.quantity, s.store_name, p.product_name",
            {"threshold": threshold}
        )
        rows = cursor.fetchall()

    _print_inventory(
        rows, f"No products have {threshold} or fewer units in stock."
    )


def add_inventory():
    """Stock a product at a store."""

    print("\n--- Add Inventory (type 'cancel' to stop) ---")

    store_id = prompt_int("Enter store ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)
    quantity = prompt_int("Enter quantity", minimum=0, maximum=MAX_QUANTITY)

    with db_session() as cursor:
        store = _store_name(cursor, store_id)
        product = _product_name(cursor, product_id)

        cursor.execute("""
            INSERT INTO Inventory (store_id, product_id, quantity)
            VALUES (:store_id, :product_id, :quantity)
        """, {
            "store_id": store_id,
            "product_id": product_id,
            "quantity": quantity
        })

    print(f"Added {quantity} x {product} to {store}.")


def update_inventory():
    """Set the quantity of an existing inventory record."""

    print("\n--- Update Inventory (set exact quantity) ---")

    store_id = prompt_int("Enter store ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)
    quantity = prompt_int(
        "Enter new quantity", minimum=0, maximum=MAX_QUANTITY
    )

    with db_session() as cursor:
        cursor.execute("""
            UPDATE Inventory
            SET quantity = :quantity
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {
            "quantity": quantity,
            "store_id": store_id,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            raise UserError("Inventory record not found for that store and product.")

    print("Inventory updated successfully!")


def adjust_inventory():
    """Add or remove units (positive or negative change)."""

    print("\n--- Adjust Inventory (+ receive stock, - remove stock) ---")

    store_id = prompt_int("Enter store ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)
    change = prompt_int(
        "Change in quantity (e.g. 25 or -5)",
        minimum=-MAX_QUANTITY, maximum=MAX_QUANTITY
    )

    if change == 0:
        raise UserError("A change of 0 does nothing.")

    with db_session() as cursor:
        # The WHERE clause makes the check-and-update a single atomic step,
        # so stock can never go negative even with concurrent users.
        cursor.execute("""
            UPDATE Inventory
            SET quantity = quantity + :change
            WHERE store_id = :store_id
              AND product_id = :product_id
              AND quantity + :change >= 0
        """, {
            "change": change,
            "store_id": store_id,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT quantity
                FROM Inventory
                WHERE store_id = :store_id AND product_id = :product_id
            """, {"store_id": store_id, "product_id": product_id})
            row = cursor.fetchone()

            if row is None:
                raise UserError(
                    "Inventory record not found for that store and product."
                )

            raise UserError(
                f"Cannot remove {-change} units: only {row[0]} in stock."
            )

        cursor.execute("""
            SELECT quantity
            FROM Inventory
            WHERE store_id = :store_id AND product_id = :product_id
        """, {"store_id": store_id, "product_id": product_id})
        new_quantity = cursor.fetchone()[0]

    print(f"Inventory adjusted. New quantity: {new_quantity}")


def delete_inventory():
    """Remove a product from a store's inventory."""

    print("\n--- Delete Inventory ---")

    store_id = prompt_int("Enter store ID", minimum=1)
    product_id = prompt_int("Enter product ID", minimum=1)

    if not confirm("Remove this inventory record"):
        print("Delete cancelled.")
        return

    with db_session() as cursor:
        cursor.execute("""
            DELETE FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {"store_id": store_id, "product_id": product_id})

        if cursor.rowcount == 0:
            raise UserError("Inventory record not found for that store and product.")

    print("Inventory record deleted successfully!")


def inventory_menu():
    """Display the inventory management menu."""

    run_menu("Inventory Management", [
        ("View All Inventory", view_inventory),
        ("View Inventory by Store", view_inventory_by_store),
        ("Search Inventory", search_inventory),
        ("Check Product Availability", check_availability),
        ("Low Stock Report", low_stock),
        ("Add Inventory Record", add_inventory),
        ("Set Quantity", update_inventory),
        ("Adjust Quantity (+/-)", adjust_inventory),
        ("Delete Inventory Record", delete_inventory),
    ])


if __name__ == "__main__":
    inventory_menu()
