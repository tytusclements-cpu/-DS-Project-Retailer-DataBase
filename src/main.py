import sys

from database import get_connection
from cli_utils import run_action

from customers import customers_menu
from inventory import inventory_menu
from orders import orders_menu
from products import products_menu
from reports import reports_menu
from sales import sales_menu
from stores import stores_menu
from vendors import vendors_menu


MENU_OPTIONS = [
    ("1", "Product Management", products_menu),
    ("2", "Store Management", stores_menu),
    ("3", "Inventory Management", inventory_menu),
    ("4", "Customer Management", customers_menu),
    ("5", "Sales Management", sales_menu),
    ("6", "Order Management", orders_menu),
    ("7", "Vendor Management", vendors_menu),
    ("8", "Reports", reports_menu),
]

EXIT_CHOICE = "9"


def check_database():
    """Return True if the database can be reached."""

    connection = get_connection()

    if connection is None:
        return False

    connection.close()
    return True


def main_menu():
    """Display the main retailer database menu."""

    while True:
        print("\n====================================")
        print("       RETAILER DATABASE SYSTEM")
        print("====================================")

        for number, label, _ in MENU_OPTIONS:
            print(f"{number}. {label}")

        print(f"{EXIT_CHOICE}. Exit")
        print("====================================")

        try:
            choice = input("Select an option: ").strip()
        except EOFError:
            print("\nInput closed. Exiting.")
            return

        if choice == EXIT_CHOICE:
            print("\nThank you for using the Retailer Database System!")
            return

        handler = next(
            (menu for number, _, menu in MENU_OPTIONS if number == choice),
            None
        )

        if handler is None:
            print(f"Invalid option. Please select 1-{EXIT_CHOICE}.")
            continue

        try:
            run_action(handler)
        except EOFError:
            print("\nInput closed. Exiting.")
            return
        except KeyboardInterrupt:
            print("\nInterrupted. Returning to the main menu.")


def main():
    if not check_database():
        print(
            "\nCould not connect to the database.\n"
            "Set RETAIL_DB_USER, RETAIL_DB_PASSWORD, RETAIL_DB_HOST, "
            "RETAIL_DB_PORT and RETAIL_DB_SERVICE (or edit database.py), "
            "and make sure the Oracle database is running."
        )
        sys.exit(1)

    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
