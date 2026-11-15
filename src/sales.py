from database import get_connection


def create_sale():
    """Create a new in-store sale."""

    print("\n--- Create Sale ---")

    store_id = input("Enter store ID: ")
    customer_id = input("Enter customer ID (leave blank for anonymous sale): ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Verify that the store exists.
        cursor.execute("""
            SELECT store_id
            FROM Stores
            WHERE store_id = :store_id
        """, {"store_id": store_id})

        if cursor.fetchone() is None:
            print("Store not found.")
            return

        # Verify customer if one was provided.
        if customer_id.strip():
            cursor.execute("""
                SELECT customer_id
                FROM Customers
                WHERE customer_id = :customer_id
            """, {"customer_id": customer_id})

            if cursor.fetchone() is None:
                print("Customer not found.")
                return
        else:
            customer_id = None

        # Create the sale and retrieve its generated ID.
        sale_id_var = cursor.var(int)

        cursor.execute("""
            INSERT INTO Sales (
                store_id, customer_id, sale_date
            )
            VALUES (
                :store_id, :customer_id, CURRENT_TIMESTAMP
            )
            RETURNING sale_id INTO :sale_id
        """, {
            "store_id": store_id,
            "customer_id": customer_id,
            "sale_id": sale_id_var
        })

        sale_id = sale_id_var.getvalue()[0]

        connection.commit()

        print(f"Sale created successfully! Sale ID: {sale_id}")

    except Exception as error:
        connection.rollback()
        print("Error creating sale:", error)

    finally:
        cursor.close()
        connection.close()


def add_sale_item():
    """Add a product to an existing sale and update inventory."""

    print("\n--- Add Product to Sale ---")

    sale_id = input("Enter sale ID: ")
    product_id = input("Enter product ID: ")

    try:
        quantity = int(input("Enter quantity: "))

        if quantity <= 0:
            print("Quantity must be greater than zero.")
            return

    except ValueError:
        print("Please enter a valid whole number.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Find the store associated with the sale.
        cursor.execute("""
            SELECT store_id
            FROM Sales
            WHERE sale_id = :sale_id
        """, {"sale_id": sale_id})

        sale = cursor.fetchone()

        if sale is None:
            print("Sale not found.")
            return

        store_id = sale[0]

        # Retrieve the product price.
        cursor.execute("""
            SELECT unit_price
            FROM Products
            WHERE product_id = :product_id
        """, {"product_id": product_id})

        product = cursor.fetchone()

        if product is None:
            print("Product not found.")
            return

        unit_price = product[0]

        # Lock the inventory record while checking stock.
        cursor.execute("""
            SELECT quantity
            FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
            FOR UPDATE
        """, {
            "store_id": store_id,
            "product_id": product_id
        })

        inventory = cursor.fetchone()

        if inventory is None:
            print("This product is not in the store's inventory.")
            return

        available_quantity = inventory[0]

        if available_quantity < quantity:
            print(
                f"Insufficient inventory. "
                f"Available quantity: {available_quantity}"
            )
            return

        # Insert the product into the sale.
        cursor.execute("""
            INSERT INTO Sale_Items (
                sale_id, product_id, quantity, unit_price
            )
            VALUES (
                :sale_id, :product_id, :quantity, :unit_price
            )
        """, {
            "sale_id": sale_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price
        })

        # Subtract purchased quantity from inventory.
        cursor.execute("""
            UPDATE Inventory
            SET quantity = quantity - :quantity
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {
            "quantity": quantity,
            "store_id": store_id,
            "product_id": product_id
        })

        connection.commit()

        print("Product added to sale successfully!")
        print(f"Inventory remaining: {available_quantity - quantity}")

    except Exception as error:
        connection.rollback()
        print("Error adding product to sale:", error)

    finally:
        cursor.close()
        connection.close()


def view_sales():
    """Display all sales transactions."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT s.sale_id,
                   s.store_id,
                   st.store_name,
                   s.customer_id,
                   s.sale_date,
                   NVL(SUM(si.quantity * si.unit_price), 0) AS total
            FROM Sales s
            JOIN Stores st
                ON s.store_id = st.store_id
            LEFT JOIN Sale_Items si
                ON s.sale_id = si.sale_id
            GROUP BY s.sale_id,
                     s.store_id,
                     st.store_name,
                     s.customer_id,
                     s.sale_date
            ORDER BY s.sale_date DESC
        """)

        sales = cursor.fetchall()

        print("\n--- Sales Transactions ---")

        if not sales:
            print("No sales found.")
            return

        for sale in sales:
            print(
                f"Sale ID: {sale[0]} | "
                f"Store: {sale[2]} | "
                f"Customer ID: {sale[3]} | "
                f"Date: {sale[4]} | "
                f"Total: ${sale[5]:.2f}"
            )

    except Exception as error:
        print("Error viewing sales:", error)

    finally:
        cursor.close()
        connection.close()


def view_sale_details():
    """Display products included in a specific sale."""

    print("\n--- Sale Details ---")

    sale_id = input("Enter sale ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT si.product_id,
                   p.product_name,
                   si.quantity,
                   si.unit_price,
                   si.quantity * si.unit_price AS subtotal
            FROM Sale_Items si
            JOIN Products p
                ON si.product_id = p.product_id
            WHERE si.sale_id = :sale_id
        """, {"sale_id": sale_id})

        items = cursor.fetchall()

        if not items:
            print("No items found for this sale.")
            return

        total = 0

        print(f"\nSale ID: {sale_id}")

        for item in items:
            print(
                f"Product: {item[1]} | "
                f"Quantity: {item[2]} | "
                f"Price: ${item[3]:.2f} | "
                f"Subtotal: ${item[4]:.2f}"
            )

            total += item[4]

        print(f"\nSale Total: ${total:.2f}")

    except Exception as error:
        print("Error retrieving sale details:", error)

    finally:
        cursor.close()
        connection.close()


def search_sales_by_store():
    """Find sales made at a particular store."""

    print("\n--- Search Sales by Store ---")

    store_id = input("Enter store ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT s.sale_id,
                   s.sale_date,
                   NVL(SUM(si.quantity * si.unit_price), 0) AS total
            FROM Sales s
            LEFT JOIN Sale_Items si
                ON s.sale_id = si.sale_id
            WHERE s.store_id = :store_id
            GROUP BY s.sale_id, s.sale_date
            ORDER BY s.sale_date DESC
        """, {"store_id": store_id})

        sales = cursor.fetchall()

        if not sales:
            print("No sales found for this store.")
            return

        for sale in sales:
            print(
                f"Sale ID: {sale[0]} | "
                f"Date: {sale[1]} | "
                f"Total: ${sale[2]:.2f}"
            )

    except Exception as error:
        print("Error searching sales:", error)

    finally:
        cursor.close()
        connection.close()


def sales_menu():
    """Display the sales management menu."""

    while True:
        print("\n===== Sales Management =====")
        print("1. Create Sale")
        print("2. Add Product to Sale")
        print("3. View All Sales")
        print("4. View Sale Details")
        print("5. Search Sales by Store")
        print("6. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            create_sale()
        elif choice == "2":
            add_sale_item()
        elif choice == "3":
            view_sales()
        elif choice == "4":
            view_sale_details()
        elif choice == "5":
            search_sales_by_store()
        elif choice == "6":
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    sales_menu()