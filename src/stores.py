from database import get_connection


def add_store():
    """Add a new store to the database."""

    print("\n--- Add Store ---")

    store_name = input("Store name: ")
    street_address = input("Street address: ")
    city = input("City: ")
    state = input("State: ")
    postal_code = input("Postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Stores (
                store_name,
                street_address,
                city,
                state,
                postal_code
            )
            VALUES (
                :store_name,
                :street_address,
                :city,
                :state,
                :postal_code
            )
        """, {
            "store_name": store_name,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code
        })

        connection.commit()
        print("Store added successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding store:", error)

    finally:
        cursor.close()
        connection.close()


def view_stores():
    """Display all stores."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT store_id,
                   store_name,
                   street_address,
                   city,
                   state,
                   postal_code
            FROM Stores
            ORDER BY store_id
        """)

        stores = cursor.fetchall()

        print("\n--- Store List ---")

        if not stores:
            print("No stores found.")
            return

        for store in stores:
            print(
                f"Store ID: {store[0]} | "
                f"Name: {store[1]} | "
                f"Address: {store[2]}, "
                f"{store[3]}, {store[4]} {store[5]}"
            )

    except Exception as error:
        print("Error viewing stores:", error)

    finally:
        cursor.close()
        connection.close()


def update_store():
    """Update an existing store's information."""

    print("\n--- Update Store ---")

    store_id = input("Enter store ID: ")
    store_name = input("New store name: ")
    street_address = input("New street address: ")
    city = input("New city: ")
    state = input("New state: ")
    postal_code = input("New postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Stores
            SET store_name = :store_name,
                street_address = :street_address,
                city = :city,
                state = :state,
                postal_code = :postal_code
            WHERE store_id = :store_id
        """, {
            "store_name": store_name,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "store_id": store_id
        })

        if cursor.rowcount == 0:
            print("Store not found.")
        else:
            connection.commit()
            print("Store updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating store:", error)

    finally:
        cursor.close()
        connection.close()


def delete_store():
    """Delete a store from the database."""

    print("\n--- Delete Store ---")

    store_id = input("Enter store ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Stores
            WHERE store_id = :store_id
        """, {
            "store_id": store_id
        })

        if cursor.rowcount == 0:
            print("Store not found.")
        else:
            connection.commit()
            print("Store deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting store:", error)
        print("The store may have existing inventory, sales, or reorders.")

    finally:
        cursor.close()
        connection.close()


def search_stores():
    """Search stores by name, city, or state."""

    print("\n--- Search Stores ---")

    search_term = input("Enter store name, city, or state: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT store_id,
                   store_name,
                   street_address,
                   city,
                   state,
                   postal_code
            FROM Stores
            WHERE LOWER(store_name) LIKE LOWER(:search)
               OR LOWER(city) LIKE LOWER(:search)
               OR LOWER(state) LIKE LOWER(:search)
            ORDER BY store_name
        """, {
            "search": f"%{search_term}%"
        })

        stores = cursor.fetchall()

        if not stores:
            print("No matching stores found.")
            return

        for store in stores:
            print(
                f"Store ID: {store[0]} | "
                f"Name: {store[1]} | "
                f"Address: {store[2]}, "
                f"{store[3]}, {store[4]} {store[5]}"
            )

    except Exception as error:
        print("Error searching stores:", error)

    finally:
        cursor.close()
        connection.close()


def stores_menu():
    """Display the store management menu."""

    while True:
        print("\n===== Store Management =====")
        print("1. Add Store")
        print("2. View Stores")
        print("3. Update Store")
        print("4. Delete Store")
        print("5. Search Stores")
        print("6. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            add_store()

        elif choice == "2":
            view_stores()

        elif choice == "3":
            update_store()

        elif choice == "4":
            delete_store()

        elif choice == "5":
            search_stores()

        elif choice == "6":
            break

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    stores_menu()