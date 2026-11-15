from database import db_session
from cli_utils import (
    UserError, delete_by_id, is_valid_email, is_valid_phone,
    is_valid_postal_code, like_pattern, print_record, print_table,
    prompt_int, prompt_text, require_row, run_menu,
)

VENDOR_COLUMNS = """
    vendor_id, vendor_name, phone, email,
    street_address, city, state, postal_code
"""

VENDOR_HEADERS = ["ID", "Name", "Phone", "Email", "City", "State"]


def _prompt_vendor_fields(current=None):
    """
    Ask for the editable vendor fields.
    current: (name, phone, email, street, city, state, postal)
    """

    def default(index):
        return None if current is None else (current[index] or "")

    return {
        "vendor_name": prompt_text(
            "Vendor name", max_len=150, default=default(0)
        ),
        "phone": prompt_text(
            "Phone", required=False, max_len=30, default=default(1),
            validator=is_valid_phone,
            error="Phone must be 7-30 digits, spaces, + - ( ) or ."
        ),
        "email": prompt_text(
            "Email", required=False, max_len=150, default=default(2),
            validator=is_valid_email,
            error="Please enter a valid email such as name@example.com."
        ),
        "street_address": prompt_text(
            "Street address", required=False, max_len=200,
            default=default(3)
        ),
        "city": prompt_text(
            "City", required=False, max_len=100, default=default(4)
        ),
        "state": prompt_text(
            "State", required=False, max_len=50, default=default(5)
        ),
        "postal_code": prompt_text(
            "Postal code", required=False, max_len=20, default=default(6),
            validator=is_valid_postal_code,
            error="Postal code must be 3-20 letters, digits, spaces or dashes."
        ),
    }


def _short_rows(rows):
    return [(r[0], r[1], r[2], r[3], r[5], r[6]) for r in rows]


def add_vendor():
    """Add a new vendor."""

    print("\n--- Add Vendor (type 'cancel' to stop) ---")

    fields = _prompt_vendor_fields()

    with db_session() as cursor:
        vendor_id = cursor.var(int)
        fields["vendor_id"] = vendor_id

        cursor.execute("""
            INSERT INTO Vendors (
                vendor_name, phone, email,
                street_address, city, state, postal_code
            )
            VALUES (
                :vendor_name, :phone, :email,
                :street_address, :city, :state, :postal_code
            )
            RETURNING vendor_id INTO :vendor_id
        """, fields)

    print(f"Vendor added successfully! Vendor ID: {vendor_id.getvalue()[0]}")


def view_vendors():
    """Display all vendors."""

    with db_session() as cursor:
        cursor.execute(f"SELECT {VENDOR_COLUMNS} FROM Vendors ORDER BY vendor_id")
        rows = cursor.fetchall()

    print("\n--- Vendor List ---")

    if not rows:
        print("No vendors found.")
        return

    print_table(VENDOR_HEADERS, _short_rows(rows))


def search_vendors():
    """Search vendors by name, city, state, or email."""

    print("\n--- Search Vendors ---")

    term = prompt_text("Enter vendor name, city, state, or email")

    with db_session() as cursor:
        cursor.execute(f"""
            SELECT {VENDOR_COLUMNS}
            FROM Vendors
            WHERE LOWER(vendor_name) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(city) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(state) LIKE LOWER(:search) ESCAPE '\\'
               OR LOWER(email) LIKE LOWER(:search) ESCAPE '\\'
            ORDER BY vendor_name
        """, {"search": like_pattern(term)})
        rows = cursor.fetchall()

    if not rows:
        print("No matching vendors found.")
        return

    print_table(VENDOR_HEADERS, _short_rows(rows))


def view_vendor_details():
    """Show one vendor with a summary of its reorders."""

    print("\n--- Vendor Details ---")

    vendor_id = prompt_int("Enter vendor ID", minimum=1)

    with db_session() as cursor:
        vendor = require_row(
            cursor,
            f"SELECT {VENDOR_COLUMNS} FROM Vendors WHERE vendor_id = :id",
            {"id": vendor_id}, f"Vendor {vendor_id} not found."
        )

        cursor.execute("""
            SELECT reorder_status, COUNT(*)
            FROM Reorders
            WHERE vendor_id = :id
            GROUP BY reorder_status
            ORDER BY reorder_status
        """, {"id": vendor_id})
        by_status = cursor.fetchall()

    print()
    print_record([
        ("Vendor ID", vendor[0]),
        ("Name", vendor[1]),
        ("Phone", vendor[2]),
        ("Email", vendor[3]),
        ("Address", ", ".join(part for part in vendor[4:8] if part)),
        ("Reorders", sum(row[1] for row in by_status)),
    ])

    for status, count in by_status:
        print(f"    {status}: {count}")


def update_vendor():
    """Update a vendor (press Enter to keep a current value)."""

    print("\n--- Update Vendor (press Enter to keep current value) ---")

    vendor_id = prompt_int("Enter vendor ID", minimum=1)

    with db_session() as cursor:
        current = require_row(
            cursor,
            """
            SELECT vendor_name, phone, email,
                   street_address, city, state, postal_code
            FROM Vendors
            WHERE vendor_id = :id
            """,
            {"id": vendor_id}, f"Vendor {vendor_id} not found."
        )

    fields = _prompt_vendor_fields(current)
    fields["vendor_id"] = vendor_id

    with db_session() as cursor:
        cursor.execute("""
            UPDATE Vendors
            SET vendor_name = :vendor_name,
                phone = :phone,
                email = :email,
                street_address = :street_address,
                city = :city,
                state = :state,
                postal_code = :postal_code
            WHERE vendor_id = :vendor_id
        """, fields)

        if cursor.rowcount == 0:
            raise UserError(f"Vendor {vendor_id} not found.")

    print("Vendor updated successfully!")


def delete_vendor():
    """Delete a vendor that has no reorders."""

    print("\n--- Delete Vendor ---")

    vendor_id = prompt_int("Enter vendor ID", minimum=1)

    delete_by_id(
        "Vendors", "vendor_id", vendor_id, "vendor", "reorder records"
    )


def view_vendor_reorders():
    """Display the reorders placed with a vendor."""

    print("\n--- Vendor Reorders ---")

    vendor_id = prompt_int("Enter vendor ID", minimum=1)

    with db_session() as cursor:
        require_row(
            cursor, "SELECT 1 FROM Vendors WHERE vendor_id = :id",
            {"id": vendor_id}, f"Vendor {vendor_id} not found."
        )

        cursor.execute("""
            SELECT r.reorder_id,
                   s.store_name,
                   r.reorder_date,
                   r.reorder_status,
                   NVL(SUM(ri.quantity), 0)
            FROM Reorders r
            JOIN Stores s ON r.store_id = s.store_id
            LEFT JOIN Reorder_Items ri ON r.reorder_id = ri.reorder_id
            WHERE r.vendor_id = :vendor_id
            GROUP BY r.reorder_id, s.store_name, r.reorder_date,
                     r.reorder_status
            ORDER BY r.reorder_date DESC
        """, {"vendor_id": vendor_id})
        rows = cursor.fetchall()

    if not rows:
        print("No reorders found for this vendor.")
        return

    print_table(
        ["Reorder ID", "Store", "Date", "Status", "Units ordered"], rows
    )


def vendors_menu():
    """Display the vendor management menu."""

    run_menu("Vendor Management", [
        ("Add Vendor", add_vendor),
        ("View Vendors", view_vendors),
        ("View Vendor Details", view_vendor_details),
        ("Update Vendor", update_vendor),
        ("Delete Vendor", delete_vendor),
        ("Search Vendors", search_vendors),
        ("View Vendor Reorders", view_vendor_reorders),
    ])


if __name__ == "__main__":
    vendors_menu()
