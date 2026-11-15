from database import get_connection


def view_inventory():
    """Display inventory for all stores."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT i.store_id,
                   s.store_name,
                   i.product_id,
                   p.product_name,
                   i.quantity
            FROM Inventory i
            JOIN Stores s ON i.store_id = s.store_id
            JOIN Products p ON i.product_id = p.product_id
            ORDER BY i.store_id, p.product_name
        """)

        records = cursor.fetchall()

        print("\n--- Inventory List ---")

        if not records:
            print("No inventory records found.")
            return

        for record in records:
            print(
                f"Store ID: {record[0]} | "
                f"Store: {record[1]} | "
                f"Product ID: {record[2]} | "
                f"Product: {record[3]} | "
                f"Quantity: {record[4]}"
            )

    except Exception as error:
        print("Error viewing inventory:", error)

    finally:
        cursor.close()
        connection.close()


def search_inventory():
    """Search inventory by store ID or product name."""

    print("\n--- Search Inventory ---")

    search_term = input("Enter store ID or product name: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT i.store_id,
                   s.store_name,
                   p.product_name,
                   i.quantity
            FROM Inventory i
            JOIN Stores s ON i.store_id = s.store_id
            JOIN Products p ON i.product_id = p.product_id
            WHERE TO_CHAR(i.store_id) = :search
               OR LOWER(p.product_name) LIKE LOWER(:product_search)
            ORDER BY s.store_name, p.product_name
        """, {
            "search": search_term,
            "product_search": f"%{search_term}%"
        })

        records = cursor.fetchall()

        if not records:
            print("No matching inventory records found.")
            return

        for record in records:
            print(
                f"Store ID: {record[0]} | "
                f"Store: {record[1]} | "
                f"Product: {record[2]} | "
                f"Quantity: {record[3]}"
            )

    except Exception as error:
        print("Error searching inventory:", error)

    finally:
        cursor.close()
        connection.close()


def add_inventory():
    """Add a product to a store's inventory."""

    print("\n--- Add Inventory ---")

    store_id = input("Enter store ID: ")
    product_id = input("Enter product ID: ")
    quantity = input("Enter quantity: ")

    try:
        quantity = int(quantity)

        if quantity < 0:
            print("Quantity cannot be negative.")
            return

    except ValueError:
        print("Please enter a valid whole number.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Inventory (
                store_id, product_id, quantity
            )
            VALUES (
                :store_id, :product_id, :quantity
            )
        """, {
            "store_id": store_id,
            "product_id": product_id,
            "quantity": quantity
        })

        connection.commit()
        print("Inventory record added successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding inventory:", error)
        print("Check that the store and product exist and the record is not already present.")

    finally:
        cursor.close()
        connection.close()


def update_inventory():
    """Update the quantity of an existing inventory record."""

    print("\n--- Update Inventory ---")

    store_id = input("Enter store ID: ")
    product_id = input("Enter product ID: ")
    quantity = input("Enter new quantity: ")

    try:
        quantity = int(quantity)

        if quantity < 0:
            print("Quantity cannot be negative.")
            return

    except ValueError:
        print("Please enter a valid whole number.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
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
            print("Inventory record not found.")
        else:
            connection.commit()
            print("Inventory updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating inventory:", error)

    finally:
        cursor.close()
        connection.close()


def delete_inventory():
    """Remove a product from a store's inventory."""

    print("\n--- Delete Inventory ---")

    store_id = input("Enter store ID: ")
    product_id = input("Enter product ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {
            "store_id": store_id,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            print("Inventory record not found.")
        else:
            connection.commit()
            print("Inventory record deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting inventory:", error)

    finally:
        cursor.close()
        connection.close()


def inventory_menu():
    """Display the inventory management menu."""

    while True:
        print("\n===== Inventory Management =====")
        print("1. View Inventory")
        print("2. Search Inventory")
        print("3. Add Inventory")
        print("4. Update Inventory")
        print("5. Delete Inventory")
        print("6. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            view_inventory()
        elif choice == "2":
            search_inventory()
        elif choice == "3":
            add_inventory()
        elif choice == "4":
            update_inventory()
        elif choice == "5":
            delete_inventory()
        elif choice == "6":
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    inventory_menu()