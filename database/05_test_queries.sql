-- 05_test_queries.sql
-- Test queries for the retail database.
-- Run after creating the tables and inserting sample data.

-- 1. Display all products with their brand and product type.
SELECT
    p.product_id,
    p.product_name,
    b.brand_name,
    pt.type_name AS product_type,
    p.unit_price
FROM Products p
JOIN Brands b
    ON p.brand_id = b.brand_id
JOIN Product_Types pt
    ON p.product_type_id = pt.product_type_id
ORDER BY p.product_name;


-- 2. Show inventory for each store.
SELECT
    s.store_name,
    p.product_name,
    i.quantity AS quantity_in_stock
FROM Inventory i
JOIN Stores s
    ON i.store_id = s.store_id
JOIN Products p
    ON i.product_id = p.product_id
ORDER BY s.store_name, p.product_name;


-- 3. Find the top 20 products by quantity sold at each store.
-- Uses the RANK function to rank products within each store.
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
    GROUP BY s.store_id, s.store_name, p.product_id, p.product_name
)
WHERE product_rank <= 20
ORDER BY store_name, product_rank;


-- 4. Find the top 5 stores by sales revenue this year.
SELECT
    store_name,
    total_sales
FROM (
    SELECT
        s.store_name,
        SUM(si.quantity * si.unit_price) AS total_sales
    FROM Stores s
    JOIN Sales sa
        ON s.store_id = sa.store_id
    JOIN Sale_Items si
        ON sa.sale_id = si.sale_id
    WHERE sa.sale_date >= TRUNC(SYSDATE, 'YYYY')
      AND sa.sale_date < ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), 12)
    GROUP BY s.store_id, s.store_name
    ORDER BY total_sales DESC
)
WHERE ROWNUM <= 5;


-- 5. Compare Coca-Cola and Pepsi sales by store.
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
GROUP BY s.store_id, s.store_name, b.brand_name
ORDER BY s.store_name, b.brand_name;


-- 6. Find products purchased in the same sale as milk.
-- DISTINCT prevents a product from appearing multiple times.
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
ORDER BY p.product_name;


-- 7. Show sales transactions with customer names and total amounts.
SELECT
    sa.sale_id,
    sa.sale_date,
    s.store_name,
    c.first_name || ' ' || c.last_name AS customer_name,
    SUM(si.quantity * si.unit_price) AS sale_total
FROM Sales sa
JOIN Stores s
    ON sa.store_id = s.store_id
LEFT JOIN Customers c
    ON sa.customer_id = c.customer_id
JOIN Sale_Items si
    ON sa.sale_id = si.sale_id
GROUP BY
    sa.sale_id,
    sa.sale_date,
    s.store_name,
    c.first_name,
    c.last_name
ORDER BY sa.sale_date DESC;


-- 8. Show web orders, customer names, and order totals.
SELECT
    wo.order_id,
    wo.order_date,
    wo.order_status,
    c.first_name || ' ' || c.last_name AS customer_name,
    SUM(woi.quantity * woi.unit_price) AS order_total
FROM Web_Orders wo
JOIN Customers c
    ON wo.customer_id = c.customer_id
JOIN Web_Order_Items woi
    ON wo.order_id = woi.order_id
GROUP BY
    wo.order_id,
    wo.order_date,
    wo.order_status,
    c.first_name,
    c.last_name
ORDER BY wo.order_date DESC;


-- 9. Show reorder details, including vendor and store.
SELECT
    r.reorder_id,
    r.reorder_date,
    r.reorder_status,
    v.vendor_name,
    s.store_name,
    p.product_name,
    ri.quantity AS quantity_ordered
FROM Reorders r
JOIN Vendors v
    ON r.vendor_id = v.vendor_id
JOIN Stores s
    ON r.store_id = s.store_id
JOIN Reorder_Items ri
    ON r.reorder_id = ri.reorder_id
JOIN Products p
    ON ri.product_id = p.product_id
ORDER BY r.reorder_date DESC, r.reorder_id;


-- 10. Show shipment status and quantities received.
SELECT
    sh.shipment_id,
    sh.shipment_status,
    sh.shipment_date,
    r.reorder_id,
    p.product_name,
    shi.quantity AS quantity_shipped
FROM Shipments sh
JOIN Reorders r
    ON sh.reorder_id = r.reorder_id
JOIN Shipment_Items shi
    ON sh.shipment_id = shi.shipment_id
JOIN Products p
    ON shi.product_id = p.product_id
ORDER BY sh.shipment_id, p.product_name;-- 05_test_queries.sql
-- Test queries for the retail database.
-- Run after creating the tables and inserting sample data.

-- 1. Display all products with their brand and product type.
SELECT
    p.product_id,
    p.product_name,
    b.brand_name,
    pt.type_name AS product_type,
    p.unit_price
FROM Products p
JOIN Brands b
    ON p.brand_id = b.brand_id
JOIN Product_Types pt
    ON p.product_type_id = pt.product_type_id
ORDER BY p.product_name;


-- 2. Show inventory for each store.
SELECT
    s.store_name,
    p.product_name,
    i.quantity AS quantity_in_stock
FROM Inventory i
JOIN Stores s
    ON i.store_id = s.store_id
JOIN Products p
    ON i.product_id = p.product_id
ORDER BY s.store_name, p.product_name;


-- 3. Find the top 20 products by quantity sold at each store.
-- Uses the RANK function to rank products within each store.
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
    GROUP BY s.store_id, s.store_name, p.product_id, p.product_name
)
WHERE product_rank <= 20
ORDER BY store_name, product_rank;


-- 4. Find the top 5 stores by sales revenue this year.
SELECT
    store_name,
    total_sales
FROM (
    SELECT
        s.store_name,
        SUM(si.quantity * si.unit_price) AS total_sales
    FROM Stores s
    JOIN Sales sa
        ON s.store_id = sa.store_id
    JOIN Sale_Items si
        ON sa.sale_id = si.sale_id
    WHERE sa.sale_date >= TRUNC(SYSDATE, 'YYYY')
      AND sa.sale_date < ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), 12)
    GROUP BY s.store_id, s.store_name
    ORDER BY total_sales DESC
)
WHERE ROWNUM <= 5;


-- 5. Compare Coca-Cola and Pepsi sales by store.
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
GROUP BY s.store_id, s.store_name, b.brand_name
ORDER BY s.store_name, b.brand_name;


-- 6. Find products purchased in the same sale as milk.
-- DISTINCT prevents a product from appearing multiple times.
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
ORDER BY p.product_name;


-- 7. Show sales transactions with customer names and total amounts.
SELECT
    sa.sale_id,
    sa.sale_date,
    s.store_name,
    c.first_name || ' ' || c.last_name AS customer_name,
    SUM(si.quantity * si.unit_price) AS sale_total
FROM Sales sa
JOIN Stores s
    ON sa.store_id = s.store_id
LEFT JOIN Customers c
    ON sa.customer_id = c.customer_id
JOIN Sale_Items si
    ON sa.sale_id = si.sale_id
GROUP BY
    sa.sale_id,
    sa.sale_date,
    s.store_name,
    c.first_name,
    c.last_name
ORDER BY sa.sale_date DESC;


-- 8. Show web orders, customer names, and order totals.
SELECT
    wo.order_id,
    wo.order_date,
    wo.order_status,
    c.first_name || ' ' || c.last_name AS customer_name,
    SUM(woi.quantity * woi.unit_price) AS order_total
FROM Web_Orders wo
JOIN Customers c
    ON wo.customer_id = c.customer_id
JOIN Web_Order_Items woi
    ON wo.order_id = woi.order_id
GROUP BY
    wo.order_id,
    wo.order_date,
    wo.order_status,
    c.first_name,
    c.last_name
ORDER BY wo.order_date DESC;


-- 9. Show reorder details, including vendor and store.
SELECT
    r.reorder_id,
    r.reorder_date,
    r.reorder_status,
    v.vendor_name,
    s.store_name,
    p.product_name,
    ri.quantity AS quantity_ordered
FROM Reorders r
JOIN Vendors v
    ON r.vendor_id = v.vendor_id
JOIN Stores s
    ON r.store_id = s.store_id
JOIN Reorder_Items ri
    ON r.reorder_id = ri.reorder_id
JOIN Products p
    ON ri.product_id = p.product_id
ORDER BY r.reorder_date DESC, r.reorder_id;


-- 10. Show shipment status and quantities received.
SELECT
    sh.shipment_id,
    sh.shipment_status,
    sh.shipment_date,
    r.reorder_id,
    p.product_name,
    shi.quantity AS quantity_shipped
FROM Shipments sh
JOIN Reorders r
    ON sh.reorder_id = r.reorder_id
JOIN Shipment_Items shi
    ON sh.shipment_id = shi.shipment_id
JOIN Products p
    ON shi.product_id = p.product_id
ORDER BY sh.shipment_id, p.product_name;