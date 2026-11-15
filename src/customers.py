from database import db_session
from cli_utils import (
    UserError, delete_by_id, is_valid_email, is_valid_phone,
    is_valid_postal_code, like_pattern, money, print_record, print_table,
    prompt_int, prompt_text, require_row, run_menu,
)

CUSTOMER_COLUMNS = """
    customer_id, first_name, last_name, email, phone,
    street_address, city, state, postal_code
"""


def _prompt_customer_fields(current=None):
    """
    Ask for the editable customer fields.
    current: (first, last, email, phone, street, city, state, postal)
    """

    def default(index):
        return None if current is None else (current[index] or "")

    return {
        "first_name": prompt_text(
            "First name", max_len=100, default=default(0)
        ),
        "last_name": prompt_text(
            "Last name", max_len=100, default=default(1)
        ),
        "email": prompt_text(
            "Email", required=False, max_len=150, default=default(2),
            validator=is_valid_email,
            error="Please enter a valid email such as name@example.com."
        ),
        "phone": prompt_text(
            "Phone", required=False, max_len=30, default=default(3),
            validator=is_valid_phone,
            error="Phone must be 7-30 digits, spaces, + - ( ) or ."
        ),
        "street_address": prompt_text(
            "Street address", required=False, max_len=200,
            default=default(4)
        ),
        "city": prompt_text(
            "City", required=False, max_len=100, default=default(5)
        ),
        "state": prompt_text(
            "State", required=False, max_len=50, default=default(6)
        ),
        "postal_code": prompt_text(
            "Postal code", required=False, max_len=20, default=default(7),
            validator=is_valid_postal_code,
            error="Postal code must be 3-20 letters, digits, spaces or dashes."
        ),
    }


def add_customer():
    """Register a new customer."""

    print("\n--- Register Customer (type 'cancel' to stop) ---")

    fields = _prompt_customer_fields()

    with db_session() as cursor:
        customer_id = cursor.var(int)
        fields["customer_id"] = customer_id

        cursor.execute("""
            INSERT INTO Customers (
                first_name, last_name, email, phone,
                street_address, city, state, postal_code
            )
            VALUES (
                :first_name, :last_name, :email, :phone,
                :street_address, :city, :state, :postal_code
            )
            RETURNING customer_id INTO :customer_id
        """, fields)

    print(
        f"Customer registered successfully! "
        f"Customer ID: {customer_id.getvalue()[0]}"
    )


def _print_customers(rows):
    print_table(
        ["ID", "First", "Last", "Email", "Phone", "City", "State"],
        [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rows]
    )


def view_customers():
    """Display all customers."""

    with db_session() as cursor:
        cursor.execute("""
            SELECT customer_id, first_name, last_name,
                   email, phone, city, state
            FROM Customers
            ORDER BY customer_id
        """)
        rows = cursor.fetchall()

    print("\n--- Customer List ---")

    if not rows:
        print("No customers found.")
        return

    _print_customers(rows)


def search_customer():
    """Search customers by name, email, or phone."""

    print("\n--- Search Customers ---")

    term = prompt_text("Enter customer name, email, or phone")

    with db_session() as cursor:
        cursor.execute("""
            SELECT customer_id, first_name, last_name,
                   email, phone, city, state
            FROM Customers
            WHERE LOWER(first_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(last_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(first_name || ' ' || last_name)
                    LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(email) LIKE LOWER(:search) ESCAPE '\\'
               OR phone LIKE :search ESCAPE '\\'
            ORDER BY last_name, first_name
        """, {"search": like_pattern(term)})
        rows = cursor.fetchall()

    if not rows:
        print("No matching customers found.")
        return

    _print_customers(rows)


def view_customer_details():
    """Show one customer with their purchase and order history."""

    print("\n--- Customer Details ---")

    customer_id = prompt_int("Enter customer ID", minimum=1)

    with db_session() as cursor:
        customer = require_row(
            cursor,
            f"SELECT {CUSTOMER_COLUMNS} FROM Customers "
            "WHERE customer_id = :id",
            {"id": customer_id}, f"Customer {customer_id} not found."
        )

        cursor.execute("""
            SELECT sa.sale_id, sa.sale_date, st.store_name,
                   NVL(SUM(si.quantity * si.unit_price), 0)
            FROM Sales sa
            JOIN Stores st ON sa.store_id = st.store_id
            LEFT JOIN Sale_Items si ON sa.sale_id = si.sale_id
            WHERE sa.customer_id = :id
            GROUP BY sa.sale_id, sa.sale_date, st.store_name
            ORDER BY sa.sale_date DESC
        """, {"id": customer_id})
        sales = cursor.fetchall()

        cursor.execute("""
            SELECT wo.order_id, wo.order_date, wo.order_status,
                   NVL(SUM(woi.quantity * woi.unit_price), 0)
            FROM Web_Orders wo
            LEFT JOIN Web_Order_Items woi ON wo.order_id = woi.order_id
            WHERE wo.customer_id = :id
            GROUP BY wo.order_id, wo.order_date, wo.order_status
            ORDER BY wo.order_date DESC
        """, {"id": customer_id})
        orders = cursor.fetchall()

    print()
    print_record([
        ("Customer ID", customer[0]),
        ("Name", f"{customer[1]} {customer[2]}"),
        ("Email", customer[3]),
        ("Phone", customer[4]),
        ("Address", ", ".join(part for part in customer[5:9] if part)),
        ("Store purchases", f"{len(sales)} totaling "
                            f"{money(sum(row[3] for row in sales))}"),
        ("Online orders", f"{len(orders)} totaling "
                          f"{money(sum(row[3] for row in orders))}"),
    ])

    if sales:
        print("\nStore purchases:")
        print_table(
            ["Sale ID", "Date", "Store", "Total"],
            [(r[0], r[1], r[2], money(r[3])) for r in sales]
        )

    if orders:
        print("\nOnline orders:")
        print_table(
            ["Order ID", "Date", "Status", "Total"],
            [(r[0], r[1], r[2], money(r[3])) for r in orders]
        )


def update_customer():
    """Update a customer (press Enter to keep a current value)."""

    print("\n--- Update Customer (press Enter to keep current value) ---")

    customer_id = prompt_int("Enter customer ID", minimum=1)

    with db_session() as cursor:
        current = require_row(
            cursor,
            """
            SELECT first_name, last_name, email, phone,
                   street_address, city, state, postal_code
            FROM Customers
            WHERE customer_id = :id
            """,
            {"id": customer_id}, f"Customer {customer_id} not found."
        )

    fields = _prompt_customer_fields(current)
    fields["customer_id"] = customer_id

    with db_session() as cursor:
        cursor.execute("""
            UPDATE Customers
            SET first_name = :first_name,
                last_name = :last_name,
                email = :email,
                phone = :phone,
                street_address = :street_address,
                city = :city,
                state = :state,
                postal_code = :postal_code
            WHERE customer_id = :customer_id
        """, fields)

        if cursor.rowcount == 0:
            raise UserError(f"Customer {customer_id} not found.")

    print("Customer updated successfully!")


def delete_customer():
    """Delete a customer who has no sales or orders."""

    print("\n--- Delete Customer ---")

    customer_id = prompt_int("Enter customer ID", minimum=1)

    delete_by_id(
        "Customers", "customer_id", customer_id, "customer",
        "sales or web orders"
    )


def customers_menu():
    """Display the customer management menu."""

    run_menu("Customer Management", [
        ("Register Customer", add_customer),
        ("View Customers", view_customers),
        ("View Customer Details", view_customer_details),
        ("Update Customer", update_customer),
        ("Delete Customer", delete_customer),
        ("Search Customers", search_customer),
    ])


if __name__ == "__main__":
    customers_menu()
