from database import db_session
from cli_utils import (
    UserError, delete_by_id, is_valid_postal_code, like_pattern, money,
    print_record, print_table, prompt_int, prompt_text, run_menu,
)

STORE_COLUMNS = """
    store_id, store_name, street_address, city, state, postal_code
"""

STORE_HEADERS = ["ID", "Name", "Street", "City", "State", "Postal code"]


def _prompt_store_fields(current=None):
    """
    Ask for the editable store fields.
    current: existing row (name, street, city, state, postal) when updating.
    """

    def default(index):
        return None if current is None else (current[index] or "")

    # An empty default on an optional field still means "keep (blank)".
    return {
        "store_name": prompt_text(
            "Store name", max_len=150, default=default(0)
        ),
        "street_address": prompt_text(
            "Street address", required=False, max_len=200,
            default=default(1)
        ),
        "city": prompt_text(
            "City", required=False, max_len=100, default=default(2)
        ),
        "state": prompt_text(
            "State", required=False, max_len=50, default=default(3)
        ),
        "postal_code": prompt_text(
            "Postal code", required=False, max_len=20, default=default(4),
            validator=is_valid_postal_code,
            error="Postal code must be 3-20 letters, digits, spaces or dashes."
        ),
    }


def add_store():
    """Add a new store."""

    print("\n--- Add Store (type 'cancel' to stop) ---")

    fields = _prompt_store_fields()

    with db_session() as cursor:
        store_id = cursor.var(int)
        fields["store_id"] = store_id

        cursor.execute("""
            INSERT INTO Stores (
                store_name, street_address, city, state, postal_code
            )
            VALUES (
                :store_name, :street_address, :city, :state, :postal_code
            )
            RETURNING store_id INTO :store_id
        """, fields)

    print(f"Store added successfully! Store ID: {store_id.getvalue()[0]}")


def view_stores():
    """Display all stores."""

    with db_session() as cursor:
        cursor.execute(f"SELECT {STORE_COLUMNS} FROM Stores ORDER BY store_id")
        rows = cursor.fetchall()

    print("\n--- Store List ---")

    if not rows:
        print("No stores found.")
        return

    print_table(STORE_HEADERS, rows)


def search_stores():
    """Search stores by name, city, or state."""

    print("\n--- Search Stores ---")

    term = prompt_text("Enter store name, city, or state")

    with db_session() as cursor:
        cursor.execute(f"""
            SELECT {STORE_COLUMNS}
            FROM Stores
            WHERE LOWER(store_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(city) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(state) LIKE LOWER(:search) ESCAPE '\\'
            ORDER BY store_name
        """, {"search": like_pattern(term)})
        rows = cursor.fetchall()

    if not rows:
        print("No matching stores found.")
        return

    print_table(STORE_HEADERS, rows)


def view_store_details():
    """Show one store with inventory, sales, and reorder summaries."""

    print("\n--- Store Details ---")

    store_id = prompt_int("Enter store ID", minimum=1)

    with db_session() as cursor:
        cursor.execute(
            f"SELECT {STORE_COLUMNS} FROM Stores WHERE store_id = :store_id",
            {"store_id": store_id}
        )
        store = cursor.fetchone()

        if store is None:
            raise UserError(f"Store {store_id} not found.")

        cursor.execute("""
            SELECT COUNT(*), NVL(SUM(quantity), 0)
            FROM Inventory
            WHERE store_id = :store_id
        """, {"store_id": store_id})
        product_lines, units = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(DISTINCT sa.sale_id),
                   NVL(SUM(si.quantity * si.unit_price), 0)
            FROM Sales sa
            LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
            WHERE sa.store_id = :store_id
        """, {"store_id": store_id})
        sale_count, revenue = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*)
            FROM Reorders
            WHERE store_id = :store_id
        """, {"store_id": store_id})
        reorder_count = cursor.fetchone()[0]

    print()
    print_record([
        ("Store ID", store[0]),
        ("Name", store[1]),
        ("Address", ", ".join(part for part in store[2:6] if part)),
        ("Products stocked", product_lines),
        ("Units in stock", units),
        ("Sales recorded", sale_count),
        ("Sales revenue", money(revenue)),
        ("Reorders placed", reorder_count),
    ])


def update_store():
    """Update a store (press Enter to keep a current value)."""

    print("\n--- Update Store (press Enter to keep current value) ---")

    store_id = prompt_int("Enter store ID", minimum=1)

    with db_session() as cursor:
        cursor.execute("""
            SELECT store_name, street_address, city, state, postal_code
            FROM Stores
            WHERE store_id = :store_id
        """, {"store_id": store_id})
        current = cursor.fetchone()

    if current is None:
        raise UserError(f"Store {store_id} not found.")

    fields = _prompt_store_fields(current)
    fields["store_id"] = store_id

    with db_session() as cursor:
        cursor.execute("""
            UPDATE Stores
            SET store_name = :store_name,
                street_address = :street_address,
                city = :city,
                state = :state,
                postal_code = :postal_code
            WHERE store_id = :store_id
        """, fields)

        if cursor.rowcount == 0:
            raise UserError(f"Store {store_id} not found.")

    print("Store updated successfully!")


def delete_store():
    """Delete a store that nothing else refers to."""

    print("\n--- Delete Store ---")

    store_id = prompt_int("Enter store ID", minimum=1)

    delete_by_id(
        "Stores", "store_id", store_id, "store",
        "inventory, sales or reorders"
    )


def stores_menu():
    """Display the store management menu."""

    run_menu("Store Management", [
        ("Add Store", add_store),
        ("View Stores", view_stores),
        ("View Store Details", view_store_details),
        ("Update Store", update_store),
        ("Delete Store", delete_store),
        ("Search Stores", search_stores),
    ])


if __name__ == "__main__":
    stores_menu()
