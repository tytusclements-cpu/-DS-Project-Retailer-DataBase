
# test_concurrency.py
# Tests concurrent database access using multiple connections.
# Uses Oracle transactions to test simultaneous inventory updates.

import threading
import oracledb

from database import (
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT,
    DB_SERVICE
)


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

def create_connection():
    """
    Creates a separate Oracle connection for each thread.
    """

    dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"

    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=dsn
    )


# --------------------------------------------------
# INVENTORY UPDATE TEST
# --------------------------------------------------

def purchase_product(store_id, product_id, quantity, results, thread_id):
    """
    Simulates a purchase by decreasing inventory.

    SELECT FOR UPDATE locks the inventory row so that
    another transaction cannot update it simultaneously.
    """

    connection = None
    cursor = None

    try:
        connection = create_connection()
        cursor = connection.cursor()

        # Lock the inventory row before reading its quantity.
        cursor.execute(
            """
            SELECT quantity
            FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
            FOR UPDATE
            """,
            {
                "store_id": store_id,
                "product_id": product_id
            }
        )

        row = cursor.fetchone()

        if row is None:
            results.append(
                f"Thread {thread_id}: Inventory record not found."
            )
            connection.rollback()
            return

        current_quantity = row[0]

        # Check whether enough inventory is available.
        if current_quantity < quantity:
            results.append(
                f"Thread {thread_id}: Not enough inventory."
            )
            connection.rollback()
            return

        # Decrease the inventory quantity.
        cursor.execute(
            """
            UPDATE Inventory
            SET quantity = quantity - :quantity
            WHERE store_id = :store_id
              AND product_id = :product_id
            """,
            {
                "quantity": quantity,
                "store_id": store_id,
                "product_id": product_id
            }
        )

        connection.commit()

        results.append(
            f"Thread {thread_id}: Purchased {quantity} units successfully."
        )

    except oracledb.Error as error:

        if connection:
            connection.rollback()

        results.append(
            f"Thread {thread_id}: Database error: {error}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# --------------------------------------------------
# READ INVENTORY QUANTITY
# --------------------------------------------------

def get_inventory_quantity(store_id, product_id):
    """
    Reads the current inventory quantity.
    """

    connection = create_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT quantity
            FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
            """,
            {
                "store_id": store_id,
                "product_id": product_id
            }
        )

        row = cursor.fetchone()

        return row[0] if row else None

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# RUN CONCURRENCY TEST
# --------------------------------------------------

def run_concurrency_test():
    """
    Starts multiple threads that attempt to purchase
    the same product from the same store.
    """

    store_id = 1
    product_id = 1

    number_of_users = 5
    purchase_quantity = 2

    print("\n========== CONCURRENCY TEST ==========")

    # Get the starting inventory quantity.
    starting_quantity = get_inventory_quantity(
        store_id,
        product_id
    )

    if starting_quantity is None:
        print("Inventory record not found.")
        return

    print("Starting inventory:", starting_quantity)
    print("Number of simulated users:", number_of_users)
    print("Quantity per purchase:", purchase_quantity)

    # Store messages from each thread.
    results = []

    # Create one thread per simulated user.
    threads = []

    for thread_id in range(1, number_of_users + 1):

        thread = threading.Thread(
            target=purchase_product,
            args=(
                store_id,
                product_id,
                purchase_quantity,
                results,
                thread_id
            )
        )

        threads.append(thread)

    # Start all threads.
    for thread in threads:
        thread.start()

    # Wait until every thread finishes.
    for thread in threads:
        thread.join()

    # Display results.
    print("\nTransaction Results:")

    for result in results:
        print(result)

    # Check the final inventory quantity.
    final_quantity = get_inventory_quantity(
        store_id,
        product_id
    )

    print("\nStarting inventory:", starting_quantity)
    print("Final inventory:", final_quantity)

    successful_purchases = sum(
        1 for result in results
        if "successfully" in result
    )

    print("Successful purchases:", successful_purchases)

    expected_quantity = (
        starting_quantity -
        successful_purchases * purchase_quantity
    )

    if final_quantity == expected_quantity:
        print("\nPASS: Inventory updates were consistent.")
    else:
        print("\nFAIL: Inventory quantities do not match expected results.")


# --------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":
    run_concurrency_test()
