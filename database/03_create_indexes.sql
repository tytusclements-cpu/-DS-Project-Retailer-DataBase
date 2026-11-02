-- 03_create_indexes.sql
-- Adds indexes to help common queries run more efficiently.
-- Run after 01_create_tables.sql and 02_create_constraints.sql.

-- Product lookups by brand or product type.
CREATE INDEX idx_products_brand
    ON Products (brand_id);

CREATE INDEX idx_products_type
    ON Products (product_type_id);

-- Inventory searches by product across stores.
-- The primary key already indexes (store_id, product_id).
CREATE INDEX idx_inventory_product
    ON Inventory (product_id);

-- Find sales for a store within a date range.
CREATE INDEX idx_sales_store_date
    ON Sales (store_id, sale_date);

-- Find sales associated with a customer.
CREATE INDEX idx_sales_customer
    ON Sales (customer_id);

-- Find products included in sales.
-- The primary key already indexes (sale_id, product_id).
CREATE INDEX idx_sale_items_product
    ON Sale_Items (product_id);

-- Find a customer's web orders by date.
CREATE INDEX idx_web_orders_customer_date
    ON Web_Orders (customer_id, order_date);

-- Find products included in web orders.
-- The primary key already indexes (order_id, product_id).
CREATE INDEX idx_web_order_items_product
    ON Web_Order_Items (product_id);

-- Find reorders for a store or vendor by date.
CREATE INDEX idx_reorders_store_date
    ON Reorders (store_id, reorder_date);

CREATE INDEX idx_reorders_vendor_date
    ON Reorders (vendor_id, reorder_date);

-- Find reorder records containing a particular product.
-- The primary key already indexes (reorder_id, product_id).
CREATE INDEX idx_reorder_items_product
    ON Reorder_Items (product_id);

-- Find shipments for a reorder.
CREATE INDEX idx_shipments_reorder
    ON Shipments (reorder_id);

-- Find products included in shipments.
-- The primary key already indexes (shipment_id, product_id).
CREATE INDEX idx_shipment_items_product
    ON Shipment_Items (product_id);