-- 02_create_constraints.sql
-- Adds additional constraints to the tables created by 01_create_tables.sql.
-- Run this script after 01_create_tables.sql.

-- Prevent duplicate store names within the same city and state.
ALTER TABLE Stores
ADD CONSTRAINT uq_stores_location_name
UNIQUE (store_name, city, state);

-- Prevent duplicate vendor names within the same city and state.
ALTER TABLE Vendors
ADD CONSTRAINT uq_vendors_location_name
UNIQUE (vendor_name, city, state);

-- Restrict order statuses to the values supported by the application.
ALTER TABLE Web_Orders
ADD CONSTRAINT ck_web_orders_status
CHECK (order_status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'));

ALTER TABLE Reorders
ADD CONSTRAINT ck_reorders_status
CHECK (reorder_status IN ('Pending', 'Ordered', 'Partially Received', 'Received', 'Cancelled'));

ALTER TABLE Shipments
ADD CONSTRAINT ck_shipments_status
CHECK (shipment_status IN ('In Transit', 'Delivered', 'Delayed', 'Cancelled'));

-- Ensure a shipment date is not earlier than the reorder date.
-- This rule is enforced by application logic or a trigger because it compares
-- values from two different tables.