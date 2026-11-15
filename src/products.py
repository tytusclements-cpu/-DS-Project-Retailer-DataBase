from database import get_connection


def add_product():
    """Add a new product to the database."""

    print("\n--- Add Product ---")

    product_name = input("Product name: ")
    brand_id = input("Brand ID: ")
    product_type_id = input("Product type ID: ")

    try:
        unit_price = float(input("Unit price: "))

        if unit_price < 0:
            print("Price cannot be negative.")
            return

    except ValueError:
        print("Please enter a valid price.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO Products (
                product_name,
                brand_id,
                product_type_id,
                unit_price
            )
            VALUES (
                :product_name,
                :brand_id,
                :product_type_id,
                :unit_price
            )
        """, {
            "product_name": product_name,
            "brand_id": brand_id,
            "product_type_id": product_type_id,
            "unit_price": unit_price
        })

        connection.commit()
        print("Product added successfully!")

    except Exception as error:
        connection.rollback()
        print("Error adding product:", error)

    finally:
        cursor.close()
        connection.close()


def view_products():
    """Display all products with their brand and product type."""

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
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
            ORDER BY p.product_id
        """)

        products = cursor.fetchall()

        print("\n--- Product List ---")

        if not products:
            print("No products found.")
            return

        for product in products:
            print(
                f"Product ID: {product[0]} | "
                f"Name: {product[1]} | "
                f"Brand: {product[2]} | "
                f"Type: {product[3]} | "
                f"Price: ${product[4]:.2f}"
            )

    except Exception as error:
        print("Error viewing products:", error)

    finally:
        cursor.close()
        connection.close()


def update_product():
    """Update an existing product."""

    print("\n--- Update Product ---")

    product_id = input("Enter product ID: ")
    product_name = input("New product name: ")
    brand_id = input("New brand ID: ")
    product_type_id = input("New product type ID: ")

    try:
        unit_price = float(input("New unit price: "))

        if unit_price < 0:
            print("Price cannot be negative.")
            return

    except ValueError:
        print("Please enter a valid price.")
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE Products
            SET product_name = :product_name,
                brand_id = :brand_id,
                product_type_id = :product_type_id,
                unit_price = :unit_price
            WHERE product_id = :product_id
        """, {
            "product_name": product_name,
            "brand_id": brand_id,
            "product_type_id": product_type_id,
            "unit_price": unit_price,
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            print("Product not found.")
        else:
            connection.commit()
            print("Product updated successfully!")

    except Exception as error:
        connection.rollback()
        print("Error updating product:", error)

    finally:
        cursor.close()
        connection.close()


def delete_product():
    """Delete a product from the database."""

    print("\n--- Delete Product ---")

    product_id = input("Enter product ID: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM Products
            WHERE product_id = :product_id
        """, {
            "product_id": product_id
        })

        if cursor.rowcount == 0:
            print("Product not found.")
        else:
            connection.commit()
            print("Product deleted successfully!")

    except Exception as error:
        connection.rollback()
        print("Error deleting product:", error)
        print("The product may be referenced by inventory, sales, or orders.")

    finally:
        cursor.close()
        connection.close()


def search_products():
    """Search for products by name or brand."""

    print("\n--- Search Products ---")

    search_term = input("Enter product name or brand: ")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
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
            WHERE LOWER(p.product_name) LIKE LOWER(:search)
               OR LOWER(b.brand_name) LIKE LOWER(:search)
            ORDER BY p.product_name
        """, {
            "search": f"%{search_term}%"
        })

        products = cursor.fetchall()

        if not products:
            print("No matching products found.")
            return

        for product in products:
            print(
                f"ID: {product[0]} | "
                f"Product: {product[1]} | "
                f"Brand: {product[2]} | "
                f"Type: {product[3]} | "
                f"Price: ${product[4]:.2f}"
            )

    except Exception as error:
        print("Error searching products:", error)

    finally:
        cursor.close()
        connection.close()


def products_menu():
    """Display the product management menu."""

    while True:
        print("\n===== Product Management =====")
        print("1. Add Product")
        print("2. View Products")
        print("3. Update Product")
        print("4. Delete Product")
        print("5. Search Products")
        print("6. Return to Main Menu")

        choice = input("Select an option: ")

        if choice == "1":
            add_product()
        elif choice == "2":
            view_products()
        elif choice == "3":
            update_product()
        elif choice == "4":
            delete_product()
        elif choice == "5":
            search_products()
        elif choice == "6":
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    products_menu()