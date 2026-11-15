from database import get_connection


def add_vendor():
    """Add a new vendor to the database."""

    print("\n--- Add Vendor ---")

    vendor_name = input("Vendor name: ")
    phone = input("Phone number: ")
    email = input("Email address: ")
    street_address = input("Street address: ")
    city = input("City: ")
    state = input("State: ")
    postal_code = input("Postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Vendors (
                vendor_name,
                phone,
                email,
                street_address,
                city,
                state,
                postal_code
            )
            VALUES (
                :vendor_name,
                :phone,
                :email,
                :street_address,
                :city,
                :state,
                :postal_code
            )
        """, {
            "vendor_name": vendor_name,
            "phone": phone,
            "email": email,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code
        })

        connection.commit()
        print("Vendor added successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding vendor:", error)

    finally:
        cursor.close()
        connection.close()


def view_vendors():
    """Display all vendors."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT vendor_id,
                   vendor_name,
                   phone,
                   email,
                   street_address,
                   city,
                   state,
                   postal_code
            FROM Vendors
            ORDER BY vendor_id
        """)

        vendors = cursor.fetchall()

        print("\n--- Vendor List ---")

        if not vendors:
            print("No vendors found.")
            return

        for vendor in vendors:
            print(
                f"Vendor ID: {vendor[0]} | "
                f"Name: {vendor[1]} | "
                f"Phone: {vendor[2]} | "
                f"Email: {vendor[3]} | "
                f"Address: {vendor[4]}, "
                f"{vendor[5]}, {vendor[6]} {vendor[7]}"
            )

    except Exception as error:
        print("Error viewing vendors:", error)

    finally:
        cursor.close()
        connection.close()


def update_vendor():
    """Update an existing vendor's information."""

    print("\n--- Update Vendor ---")

    vendor_id = input("Enter vendor ID: ")
    vendor_name = input("New vendor name: ")
    phone = input("New phone number: ")
    email = input("New email address: ")
    street_address = input("New street address: ")
    city = input("New city: ")
    state = input("New state: ")
    postal_code = input("New postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
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
        """, {
            "vendor_name": vendor_name,
            "phone": phone,
            "email": email,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "vendor_id": vendor_id
        })

        if cursor.rowcount == 0:
            print("Vendor not found.")
        else:
            connection.commit()
            print("Vendor updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating vendor:", error)

    finally:
        cursor.close()
        connection.close()


def delete_vendor():
    """Delete a vendor from the database."""

    print("\n--- Delete Vendor ---")

    vendor_id = input("Enter vendor ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Vendors
            WHERE vendor_id = :vendor_id
        """, {
            "vendor_id": vendor_id
        })

        if cursor.rowcount == 0:
            print("Vendor not found.")
        else:
            connection.commit()
            print("Vendor deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting vendor:", error)
        print("The vendor may have existing reorder records.")

    finally:
        cursor.close()
        connection.close()


def search_vendors():
    """Search vendors by name, city, or email."""

    print("\n--- Search Vendors ---")

    search_term = input("Enter vendor name, city, or email: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT vendor_id,
                   vendor_name,
                   phone,
                   email,
                   city,
                   state
            FROM Vendors
            WHERE LOWER(vendor_name) LIKE LOWER(:search)
               OR LOWER(city) LIKE LOWER(:search)
               OR LOWER(email) LIKE LOWER(:search)
            ORDER BY vendor_name
        """, {
            "search": f"%{search_term}%"
        })

        vendors = cursor.fetchall()

        if not vendors:
            print("No matching vendors found.")
            return

        for vendor in vendors:
            print(
                f"Vendor ID: {vendor[0]} | "
                f"Name: {vendor[1]} | "
                f"Phone: {vendor[2]} | "
                f"Email: {vendor[3]} | "
                f"Location: {vendor[4]}, {vendor[5]}"
            )

    except Exception as error:
        print("Error searching vendors:", error)

    finally:
        cursor.close()
        connection.close()


def view_vendor_reorders():
    """Display reorder records associated with a vendor."""

    print("\n--- Vendor Reorders ---")

    vendor_id = input("Enter vendor ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT r.reorder_id,
                   r.store_id,
                   s.store_name,
                   r.reorder_date,
                   r.reorder_status
            FROM Reorders r
            JOIN Stores s
                ON r.store_id = s.store_id
            WHERE r.vendor_id = :vendor_id
            ORDER BY r.reorder_date DESC
        """, {
            "vendor_id": vendor_id
        })

        reorders = cursor.fetchall()

        if not reorders:
            print("No reorders found for this vendor.")
            return

        for reorder in reorders:
            print(
                f"Reorder ID: {reorder[0]} | "
                f"Store: {reorder[2]} | "
                f"Date: {reorder[3]} | "
                f"Status: {reorder[4]}"
            )

    except Exception as error:
        print("Error retrieving vendor reorders:", error)

    finally:
        cursor.close()
        connection.close()


def vendors_menu():
    """Display the vendor management menu."""

    while True:
        print("\n===== Vendor Management =====")
        print("1. Add Vendor")
        print("2. View Vendors")
        print("3. Update Vendor")
        print("4. Delete Vendor")
        print("5. Search Vendors")
        print("6. View Vendor Reorders")
        print("7. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            add_vendor()

        elif choice == "2":
            view_vendors()

        elif choice == "3":
            update_vendor()

        elif choice == "4":
            delete_vendor()

        elif choice == "5":
            search_vendors()

        elif choice == "6":
            view_vendor_reorders()

        elif choice == "7":
            break

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    vendors_menu()