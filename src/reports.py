
# reports.py
# Generates reports for the retail database.
# Uses database.py to connect to Oracle and execute SQL queries.

from database import execute_query


# --------------------------------------------------
# 1. TOP 20 PRODUCTS BY STORE
# --------------------------------------------------

def top_products_by_store():
    """
    Displays the top 20 products sold at each store.
    Products are ranked by total quantity sold.
    """

    sql = """
        SELECT
            store_name,
            product_name,
            total_quantity_sold,
            product_rank
        FROM (
            SELECT
                s.store_name,
                p.product_name,
                SUM(si.quantity) AS total_quantity_sold,
                RANK() OVER (
                    PARTITION BY s.store_id
                    ORDER BY SUM(si.quantity) DESC
                ) AS product_rank
            FROM Sales sa
            JOIN Stores s
                ON sa.store_id = s.store_id
            JOIN Sale_Items si
                ON sa.sale_id = si.sale_id
            JOIN Products p
                ON si.product_id = p.product_id
            GROUP BY
                s.store_id,
                s.store_name,
                p.product_id,
                p.product_name
        )
        WHERE product_rank <= 20
        ORDER BY store_name, product_rank
    """

    return execute_query(sql)


# --------------------------------------------------
# 2. TOP 5 STORES BY SALES THIS YEAR
# --------------------------------------------------

def top_stores_by_sales():
    """
    Finds the five stores with the highest sales revenue
    during the current calendar year.
    """

    sql = """
        SELECT *
        FROM (
            SELECT
                s.store_id,
                s.store_name,
                SUM(si.quantity * si.unit_price) AS total_sales
            FROM Stores s
            JOIN Sales sa
                ON s.store_id = sa.store_id
            JOIN Sale_Items si
                ON sa.sale_id = si.sale_id
            WHERE sa.sale_date >= TRUNC(SYSDATE, 'YYYY')
              AND sa.sale_date < ADD_MONTHS(
                  TRUNC(SYSDATE, 'YYYY'), 12
              )
            GROUP BY s.store_id, s.store_name
            ORDER BY total_sales DESC
        )
        WHERE ROWNUM <= 5
    """

    return execute_query(sql)


# --------------------------------------------------
# 3. COCA-COLA VS PEPSI SALES COMPARISON
# --------------------------------------------------

def compare_coke_pepsi():
    """
    Compares Coca-Cola and Pepsi sales at each store.
    Displays units sold and total sales revenue.
    """

    sql = """
        SELECT
            s.store_name,
            b.brand_name,
            SUM(si.quantity) AS units_sold,
            SUM(si.quantity * si.unit_price) AS sales_revenue
        FROM Sales sa
        JOIN Stores s
            ON sa.store_id = s.store_id
        JOIN Sale_Items si
            ON sa.sale_id = si.sale_id
        JOIN Products p
            ON si.product_id = p.product_id
        JOIN Brands b
            ON p.brand_id = b.brand_id
        WHERE b.brand_name IN ('Coca-Cola', 'PepsiCo')
        GROUP BY
            s.store_id,
            s.store_name,
            b.brand_name
        ORDER BY s.store_name, b.brand_name
    """

    return execute_query(sql)


# --------------------------------------------------
# 4. PRODUCTS PURCHASED WITH MILK
# --------------------------------------------------

def products_bought_with_milk():
    """
    Finds products purchased in the same sale as milk.
    """

    sql = """
        SELECT DISTINCT
            p.product_name
        FROM Sale_Items milk_item
        JOIN Products milk
            ON milk_item.product_id = milk.product_id
        JOIN Sale_Items other_item
            ON milk_item.sale_id = other_item.sale_id
        JOIN Products p
            ON other_item.product_id = p.product_id
        WHERE LOWER(milk.product_name) LIKE '%milk%'
          AND p.product_id <> milk.product_id
        ORDER BY p.product_name
    """

    return execute_query(sql)


# --------------------------------------------------
# 5. INVENTORY REPORT
# --------------------------------------------------

def inventory_report():
    """
    Displays the current inventory quantities
    for every product at each store.
    """

    sql = """
        SELECT
            s.store_name,
            p.product_name,
            i.quantity AS quantity_in_stock
        FROM Inventory i
        JOIN Stores s
            ON i.store_id = s.store_id
        JOIN Products p
            ON i.product_id = p.product_id
        ORDER BY s.store_name, p.product_name
    """

    return execute_query(sql)


# --------------------------------------------------
# 6. CUSTOMER SALES HISTORY
# --------------------------------------------------

def customer_sales_history():
    """
    Displays sales associated with each customer.
    """

    sql = """
        SELECT
            c.customer_id,
            c.first_name || ' ' || c.last_name AS customer_name,
            sa.sale_id,
            sa.sale_date,
            s.store_name,
            SUM(si.quantity * si.unit_price) AS sale_total
        FROM Customers c
        JOIN Sales sa
            ON c.customer_id = sa.customer_id
        JOIN Stores s
            ON sa.store_id = s.store_id
        JOIN Sale_Items si
            ON sa.sale_id = si.sale_id
        GROUP BY
            c.customer_id,
            c.first_name,
            c.last_name,
            sa.sale_id,
            sa.sale_date,
            s.store_name
        ORDER BY c.customer_id, sa.sale_date DESC
    """

    return execute_query(sql)


# --------------------------------------------------
# 7. ONLINE ORDER REPORT
# --------------------------------------------------

def online_order_report():
    """
    Displays online orders, customer names,
    order statuses, and order totals.
    """

    sql = """
        SELECT
            wo.order_id,
            c.first_name || ' ' || c.last_name AS customer_name,
            wo.order_date,
            wo.order_status,
            SUM(woi.quantity * woi.unit_price) AS order_total
        FROM Web_Orders wo
        JOIN Customers c
            ON wo.customer_id = c.customer_id
        JOIN Web_Order_Items woi
            ON wo.order_id = woi.order_id
        GROUP BY
            wo.order_id,
            c.first_name,
            c.last_name,
            wo.order_date,
            wo.order_status
        ORDER BY wo.order_date DESC
    """

    return execute_query(sql)


# --------------------------------------------------
# 8. VENDOR REORDER REPORT
# --------------------------------------------------

def vendor_reorder_report():
    """
    Displays reorder information, including vendors,
    stores, products, and requested quantities.
    """

    sql = """
        SELECT
            r.reorder_id,
            v.vendor_name,
            s.store_name,
            p.product_name,
            ri.quantity AS quantity_ordered,
            r.reorder_date,
            r.reorder_status
        FROM Reorders r
        JOIN Vendors v
            ON r.vendor_id = v.vendor_id
        JOIN Stores s
            ON r.store_id = s.store_id
        JOIN Reorder_Items ri
            ON r.reorder_id = ri.reorder_id
        JOIN Products p
            ON ri.product_id = p.product_id
        ORDER BY r.reorder_date DESC
    """

    return execute_query(sql)


# --------------------------------------------------
# 9. SHIPMENT REPORT
# --------------------------------------------------

def shipment_report():
    """
    Displays shipment details and product quantities.
    """

    sql = """
        SELECT
            sh.shipment_id,
            r.reorder_id,
            sh.shipment_date,
            sh.shipment_status,
            p.product_name,
            shi.quantity AS quantity_shipped
        FROM Shipments sh
        JOIN Reorders r
            ON sh.reorder_id = r.reorder_id
        JOIN Shipment_Items shi
            ON sh.shipment_id = shi.shipment_id
        JOIN Products p
            ON shi.product_id = p.product_id
        ORDER BY sh.shipment_id
    """

    return execute_query(sql)


# --------------------------------------------------
# DISPLAY REPORT RESULTS
# --------------------------------------------------

def display_report(title, results):
    """
    Prints report results in a readable format.
    """

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    if not results:
        print("No records found.")
        return

    for row in results:
        print(row)

    print("=" * 70)


# --------------------------------------------------
# REPORT MENU
# --------------------------------------------------

def reports_menu():
    """
    Allows users to select which database report to run.
    """

    reports = {
        "1": ("Top 20 Products by Store", top_products_by_store),
        "2": ("Top 5 Stores by Sales", top_stores_by_sales),
        "3": ("Coca-Cola vs Pepsi Sales", compare_coke_pepsi),
        "4": ("Products Bought with Milk", products_bought_with_milk),
        "5": ("Inventory Report", inventory_report),
        "6": ("Customer Sales History", customer_sales_history),
        "7": ("Online Order Report", online_order_report),
        "8": ("Vendor Reorder Report", vendor_reorder_report),
        "9": ("Shipment Report", shipment_report)
    }

    while True:

        print("\n========== RETAIL DATABASE REPORTS ==========")

        for number, (title, _) in reports.items():
            print(f"{number}. {title}")

        print("0. Return to Main Menu")

        choice = input("\nSelect a report: ").strip()

        if choice == "0":
            break

        if choice in reports:

            title, report_function = reports[choice]

            try:
                results = report_function()
                display_report(title, results)

            except Exception as error:
                print("Error generating report:", error)

        else:
            print("Invalid selection. Please try again.")


# --------------------------------------------------
# RUN REPORTS DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":
    reports_menu()
