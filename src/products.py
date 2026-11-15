from database import db_session
from cli_utils import (
    UserError, delete_by_id, like_pattern, money, print_record, print_table,
    prompt_int, prompt_money, prompt_text, run_menu,
)

PRODUCT_SELECT = """
    SELECT p.product_id,
           p.product_name,
           b.brand_name,
           pt.type_name,
           p.unit_price
    FROM Products p
    JOIN Brands b
        ON p.brand_id = b.brand_id
    JOIN Product_Types pt
        ON p.product_type_id = pt.product_type_id
"""

PRODUCT_HEADERS = ["ID", "Product", "Brand", "Type", "Price"]


def _product_rows(rows):
    return [(r[0], r[1], r[2], r[3], money(r[4])) for r in rows]


def _choose_reference(table, id_column, name_column, label, current_id=None):
    """
    Let the user pick a brand or product type from the existing list, or type
    "new" to create one.

    Returns ("id", existing_id) or ("new", new_name).
    """

    with db_session() as cursor:
        cursor.execute(
            f"SELECT {id_column}, {name_column} FROM {table} "
            f"ORDER BY {name_column}"
        )
        options = cursor.fetchall()

    print(f"\nAvailable {label}s:")
    print_table(["ID", label.capitalize()], options)

    valid_ids = {row[0] for row in options}

    while True:
        answer = prompt_text(
            f"{label.capitalize()} ID (or 'new' to create one)",
            default=None if current_id is None else str(current_id)
        )

        if answer.lower() == "new":
            name = prompt_text(f"New {label} name", max_len=100)
            return ("new", name)

        if answer.isdigit() and int(answer) in valid_ids:
            return ("id", int(answer))

        print(f"No {label} with that ID. Choose from the list or type 'new'.")


def _resolve_reference(cursor, table, id_column, name_column, choice):
    """Turn a _choose_reference result into an ID, creating the row if new."""

    kind, value = choice

    if kind == "id":
        return value

    # Reuse an existing row with the same name instead of failing on UNIQUE.
    cursor.execute(
        f"SELECT {id_column} FROM {table} "
        f"WHERE LOWER({name_column}) = LOWER(:name)",
        {"name": value}
    )
    existing = cursor.fetchone()

    if existing:
        return existing[0]

    new_id = cursor.var(int)
    cursor.execute(
        f"INSERT INTO {table} ({name_column}) VALUES (:name) "
        f"RETURNING {id_column} INTO :new_id",
        {"name": value, "new_id": new_id}
    )

    return new_id.getvalue()[0]


def _fetch_product(cursor, product_id):
    cursor.execute(
        PRODUCT_SELECT + " WHERE p.product_id = :product_id",
        {"product_id": product_id}
    )
    row = cursor.fetchone()

    if row is None:
        raise UserError(f"Product {product_id} not found.")

    return row


def add_product():
    """Add a new product."""

    print("\n--- Add Product (type 'cancel' to stop) ---")

    name = prompt_text("Product name", max_len=150)
    brand_choice = _choose_reference(
        "Brands", "brand_id", "brand_name", "brand"
    )
    type_choice = _choose_reference(
        "Product_Types", "product_type_id", "type_name", "type"
    )
    price = prompt_money("Unit price")

    with db_session() as cursor:
        brand_id = _resolve_reference(
            cursor, "Brands", "brand_id", "brand_name", brand_choice
        )
        type_id = _resolve_reference(
            cursor, "Product_Types", "product_type_id", "type_name",
            type_choice
        )

        product_id = cursor.var(int)
        cursor.execute("""
            INSERT INTO Products (
                product_name, brand_id, product_type_id, unit_price
            )
            VALUES (
                :product_name, :brand_id, :product_type_id, :unit_price
            )
            RETURNING product_id INTO :product_id
        """, {
            "product_name": name,
            "brand_id": brand_id,
            "product_type_id": type_id,
            "unit_price": price,
            "product_id": product_id
        })

    print(f"Product added successfully! Product ID: {product_id.getvalue()[0]}")


def view_products():
    """Display all products."""

    with db_session() as cursor:
        cursor.execute(PRODUCT_SELECT + " ORDER BY p.product_id")
        rows = cursor.fetchall()

    print("\n--- Product List ---")

    if not rows:
        print("No products found.")
        return

    print_table(PRODUCT_HEADERS, _product_rows(rows))


def search_products():
    """Search products by name, brand, or type."""

    print("\n--- Search Products ---")

    term = prompt_text("Enter product name, brand, or type")

    with db_session() as cursor:
        cursor.execute(PRODUCT_SELECT + """
            WHERE LOWER(p.product_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(b.brand_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(pt.type_name) LIKE LOWER(:search) ESCAPE '\\'
            ORDER BY p.product_name
        """, {"search": like_pattern(term)})
        rows = cursor.fetchall()

    if not rows:
        print("No matching products found.")
        return

    print_table(PRODUCT_HEADERS, _product_rows(rows))


def view_product_details():
    """Show one product with its stock levels and sales history."""

    print("\n--- Product Details ---")

    product_id = prompt_int("Enter product ID", minimum=1)

    with db_session() as cursor:
        product = _fetch_product(cursor, product_id)

        cursor.execute("""
            SELECT s.store_id, s.store_name, i.quantity
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
        units_ordered_online = cursor.fetchone()[0]

    print()
    print_record([
        ("Product ID", product[0]),
        ("Name", product[1]),
        ("Brand", product[2]),
        ("Type", product[3]),
        ("Unit price", money(product[4])),
        ("Units sold in store", units_sold),
        ("Store sales revenue", money(revenue)),
        ("Units on web orders", units_ordered_online),
        ("Total units in stock", sum(row[2] for row in stock)),
    ])

    print("\nStock by store:")

    if stock:
        print_table(["Store ID", "Store", "Quantity"], stock)
    else:
        print("  Not stocked at any store.")


def update_product():
    """Update an existing product (press Enter to keep a current value)."""

    print("\n--- Update Product (press Enter to keep current value) ---")

    product_id = prompt_int("Enter product ID", minimum=1)

    with db_session() as cursor:
        cursor.execute("""
            SELECT product_name, brand_id, product_type_id, unit_price
            FROM Products
            WHERE product_id = :product_id
        """, {"product_id": product_id})
        current = cursor.fetchone()

    if current is None:
        raise UserError(f"Product {product_id} not found.")

    name = prompt_text("Product name", max_len=150, default=current[0])
    brand_choice = _choose_reference(
        "Brands", "brand_id", "brand_name", "brand", current_id=current[1]
    )
    type_choice = _choose_reference(
        "Product_Types", "product_type_id", "type_name", "type",
        current_id=current[2]
    )
    price = prompt_money("Unit price", default=current[3])

    with db_session() as cursor:
        brand_id = _resolve_reference(
            cursor, "Brands", "brand_id", "brand_name", brand_choice
        )
        type_id = _resolve_reference(
            cursor, "Product_Types", "product_type_id", "type_name",
            type_choice
        )

        cursor.execute("""
            UPDATE Products
            SET product_name = :product_name,
                brand_id = :brand_id,
                product_type_id = :product_type_id,
                unit_price = :unit_price
            WHERE product_id = :product_id
        """, {
            "product_name": name,
            "brand_id": brand_id,
            "product_type_id": type_id,
            "unit_price": price,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            raise UserError(f"Product {product_id} not found.")

    print("Product updated successfully!")


def delete_product():
    """Delete a product that nothing else refers to."""

    print("\n--- Delete Product ---")

    product_id = prompt_int("Enter product ID", minimum=1)

    delete_by_id(
        "Products", "product_id", product_id, "product",
        "inventory, sales, orders, reorders or shipments"
    )


def products_menu():
    """Display the product management menu."""

    run_menu("Product Management", [
        ("Add Product", add_product),
        ("View Products", view_products),
        ("View Product Details", view_product_details),
        ("Update Product", update_product),
        ("Delete Product", delete_product),
        ("Search Products", search_products),
    ])


if __name__ == "__main__":
    products_menu()
