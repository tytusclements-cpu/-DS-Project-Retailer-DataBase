from database import get_connection


def add_customer():
    """Add a new customer to the database."""

    print("\n--- Add Customer ---")

    first_name = input("First name: ")
    last_name = input("Last name: ")
    email = input("Email: ")
    phone = input("Phone: ")
    street_address = input("Street address: ")
    city = input("City: ")
    state = input("State: ")
    postal_code = input("Postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Customers (
                first_name, last_name, email, phone,
                street_address, city, state, postal_code
            )
            VALUES (
                :first_name, :last_name, :email, :phone,
                :street_address, :city, :state, :postal_code
            )
        """, {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code
        })

        connection.commit()
        print("Customer added successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding customer:", error)

    finally:
        cursor.close()
        connection.close()


def view_customers():
    """Display all customers."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT customer_id, first_name, last_name,
                   email, phone, city, state
            FROM Customers
            ORDER BY customer_id
        """)

        customers = cursor.fetchall()

        print("\n--- Customer List ---")

        if not customers:
            print("No customers found.")
            return

        for customer in customers:
            print(
                f"ID: {customer[0]} | "
                f"Name: {customer[1]} {customer[2]} | "
                f"Email: {customer[3]} | "
                f"Phone: {customer[4]} | "
                f"Location: {customer[5]}, {customer[6]}"
            )

    except Exception as error:
        print("Error retrieving customers:", error)

    finally:
        cursor.close()
        connection.close()


def update_customer():
    """Update an existing customer's information."""

    print("\n--- Update Customer ---")

    customer_id = input("Enter customer ID: ")

    first_name = input("New first name: ")
    last_name = input("New last name: ")
    email = input("New email: ")
    phone = input("New phone: ")
    street_address = input("New street address: ")
    city = input("New city: ")
    state = input("New state: ")
    postal_code = input("New postal code: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
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
        """, {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "street_address": street_address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "customer_id": customer_id
        })

        if cursor.rowcount == 0:
            print("Customer not found.")
        else:
            connection.commit()
            print("Customer updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating customer:", error)

    finally:
        cursor.close()
        connection.close()


def delete_customer():
    """Delete a customer from the database."""

    print("\n--- Delete Customer ---")

    customer_id = input("Enter customer ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Customers
            WHERE customer_id = :customer_id
        """, {
            "customer_id": customer_id
        })

        if cursor.rowcount == 0:
            print("Customer not found.")
        else:
            connection.commit()
            print("Customer deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting customer:", error)
        print("The customer may have existing sales or web orders.")

    finally:
        cursor.close()
        connection.close()


def search_customer():
    """Search for a customer using their name or email."""

    print("\n--- Search Customer ---")

    search_term = input("Enter customer name or email: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT customer_id, first_name, last_name,
                   email, phone
            FROM Customers
            WHERE LOWER(first_name) LIKE LOWER(:search)
               OR LOWER(last_name) LIKE LOWER(:search)
               OR LOWER(email) LIKE LOWER(:search)
        """, {
            "search": f"%{search_term}%"
        })

        customers = cursor.fetchall()

        if not customers:
            print("No matching customers found.")
            return

        for customer in customers:
            print(
                f"ID: {customer[0]} | "
                f"Name: {customer[1]} {customer[2]} | "
                f"Email: {customer[3]} | "
                f"Phone: {customer[4]}"
            )

    except Exception as error:
        print("Error searching customers:", error)

    finally:
        cursor.close()
        connection.close()


def customers_menu():
    """Display the customer management menu."""

    while True:
        print("\n===== Customer Management =====")
        print("1. Add Customer")
        print("2. View Customers")
        print("3. Update Customer")
        print("4. Delete Customer")
        print("5. Search Customer")
        print("6. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            add_customer()
        elif choice == "2":
            view_customers()
        elif choice == "3":
            update_customer()
        elif choice == "4":
            delete_customer()
        elif choice == "5":
            search_customer()
        elif choice == "6":
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    customers_menu()