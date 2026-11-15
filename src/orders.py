from database import get_connection


def create_order():
    """Create a new online order for a customer."""

    print("\n--- Create Online Order ---")

    customer_id = input("Enter customer ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Verify that the customer exists.
        cursor.execute("""
            SELECT customer_id
            FROM Customers
            WHERE customer_id = :customer_id
        """, {"customer_id": customer_id})

        if cursor.fetchone() is None:
            print("Customer not found.")
            return

        # Create the order.
        cursor.execute("""
            INSERT INTO Web_Orders (
                customer_id, order_date, order_status
            )
            VALUES (
                :customer_id, CURRENT_TIMESTAMP, 'Pending'
            )
            RETURNING order_id INTO :order_id
        """, {
            "customer_id": customer_id,
            "order_id": cursor.var(int)
        })

        order_id = cursor.getimplicitresults() if False else None

        # Retrieve the newly created order ID.
        cursor.execute("""
            SELECT MAX(order_id)
            FROM Web_Orders
            WHERE customer_id = :customer_id
        """, {"customer_id": customer_id})

        order_id = cursor.fetchone()[0]

        connection.commit()

        print(f"Order created successfully! Order ID: {order_id}")

    except Exception as error:
        connection.rollback()
        print("Error creating order:", error)

    finally:
        cursor.close()
        connection.close()


def view_orders():
    """Display all online orders."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT o.order_id,
                   o.customer_id,
                   c.first_name,
                   c.last_name,
                   o.order_date,
                   o.order_status
            FROM Web_Orders o
            JOIN Customers c
                ON o.customer_id = c.customer_id
            ORDER BY o.order_date DESC
        """)

        orders = cursor.fetchall()

        print("\n--- Online Orders ---")

        if not orders:
            print("No orders found.")
            return

        for order in orders:
            print(
                f"Order ID: {order[0]} | "
                f"Customer ID: {order[1]} | "
                f"Customer: {order[2]} {order[3]} | "
                f"Date: {order[4]} | "
                f"Status: {order[5]}"
            )

    except Exception as error:
        print("Error viewing orders:", error)

    finally:
        cursor.close()
        connection.close()


def view_order_details():
    """Display the products and quantities in an order."""

    print("\n--- Order Details ---")

    order_id = input("Enter order ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT oi.product_id,
                   p.product_name,
                   oi.quantity,
                   oi.unit_price,
                   oi.quantity * oi.unit_price AS subtotal
            FROM Web_Order_Items oi
            JOIN Products p
                ON oi.product_id = p.product_id
            WHERE oi.order_id = :order_id
        """, {"order_id": order_id})

        items = cursor.fetchall()

        if not items:
            print("No items found for this order.")
            return

        total = 0

        print(f"\nOrder ID: {order_id}")

        for item in items:
            print(
                f"Product: {item[1]} | "
                f"Quantity: {item[2]} | "
                f"Unit Price: ${item[3]:.2f} | "
                f"Subtotal: ${item[4]:.2f}"
            )

            total += item[4]

        print(f"Order Total: ${total:.2f}")

    except Exception as error:
        print("Error retrieving order details:", error)

    finally:
        cursor.close()
        connection.close()


def add_order_item():
    """Add a product to an existing online order."""

    print("\n--- Add Product to Order ---")

    order_id = input("Enter order ID: ")
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
        # Check that the order exists and is still pending.
        cursor.execute("""
            SELECT order_status
            FROM Web_Orders
            WHERE order_id = :order_id
        """, {"order_id": order_id})

        order = cursor.fetchone()

        if order is None:
            print("Order not found.")
            return

        if order[0] != "Pending":
            print("Products can only be added to pending orders.")
            return

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

        # Add the product to the order.
        cursor.execute("""
            INSERT INTO Web_Order_Items (
                order_id, product_id, quantity, unit_price
            )
            VALUES (
                :order_id, :product_id, :quantity, :unit_price
            )
        """, {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price
        })

        connection.commit()
        print("Product added to order successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding order item:", error)

    finally:
        cursor.close()
        connection.close()


def update_order_status():
    """Update the status of an online order."""

    print("\n--- Update Order Status ---")

    order_id = input("Enter order ID: ")

    print("\nAvailable statuses:")
    print("1. Pending")
    print("2. Processing")
    print("3. Shipped")
    print("4. Delivered")
    print("5. Cancelled")

    statuses = {
        "1": "Pending",
        "2": "Processing",
        "3": "Shipped",
        "4": "Delivered",
        "5": "Cancelled"
    }

    choice = input("Select new status: ")

    if choice not in statuses:
        print("Invalid status selection.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Web_Orders
            SET order_status = :status
            WHERE order_id = :order_id
        """, {
            "status": statuses[choice],
            "order_id": order_id
        })

        if cursor.rowcount == 0:
            print("Order not found.")
        else:
            connection.commit()
            print("Order status updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating order:", error)

    finally:
        cursor.close()
        connection.close()


def delete_order():
    """Delete an online order and its associated items."""

    print("\n--- Delete Online Order ---")

    order_id = input("Enter order ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Delete order items first because of the foreign key.
        cursor.execute("""
            DELETE FROM Web_Order_Items
            WHERE order_id = :order_id
        """, {"order_id": order_id})

        # Delete the order.
        cursor.execute("""
            DELETE FROM Web_Orders
            WHERE order_id = :order_id
        """, {"order_id": order_id})

        if cursor.rowcount == 0:
            print("Order not found.")
        else:
            connection.commit()
            print("Order deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting order:", error)

    finally:
        cursor.close()
        connection.close()


def orders_menu():
    """Display the online order management menu."""

    while True:
        print("\n===== Online Order Management =====")
        print("1. Create Order")
        print("2. View All Orders")
        print("3. View Order Details")
        print("4. Add Product to Order")
        print("5. Update Order Status")
        print("6. Delete Order")
        print("7. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            create_order()
        elif choice == "2":
            view_orders()
        elif choice == "3":
            view_order_details()
        elif choice == "4":
            add_order_item()
        elif choice == "5":
            update_order_status()
        elif choice == "6":
            delete_order()
        elif choice == "7":
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    orders_menu()