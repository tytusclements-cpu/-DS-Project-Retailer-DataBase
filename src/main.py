from customers import customers_menu
from inventory import inventory_menu
from reports import reports_menu

# Import other project modules
from products import products_menu
from stores import stores_menu
from sales import sales_menu
from orders import orders_menu
from vendors import vendors_menu


def main_menu():
    """Display the main retailer database menu."""

    while True:
        print("\n====================================")
        print("       RETAILER DATABASE SYSTEM")
        print("====================================")
        print("1. Product Management")
        print("2. Store Management")
        print("3. Inventory Management")
        print("4. Customer Management")
        print("5. Sales Management")
        print("6. Online Order Management")
        print("7. Vendor Management")
        print("8. Reports")
        print("9. Exit")
        print("====================================")

        choice = input("Select an option: ")

        if choice == "1":
            products_menu()

        elif choice == "2":
            stores_menu()

        elif choice == "3":
            inventory_menu()

        elif choice == "4":
            customers_menu()

        elif choice == "5":
            sales_menu()

        elif choice == "6":
            orders_menu()

        elif choice == "7":
            vendors_menu()

        elif choice == "8":
            reports_menu()

        elif choice == "9":
            print("\nThank you for using the Retailer Database System!")
            break

        else:
            print("Invalid option. Please select 1-9.")


if __name__ == "__main__":
    main_menu()