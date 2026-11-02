-- 04_insert_sample_data.sql
-- Inserts sample data for testing the retail database.
-- Run after the table, constraint, and index scripts.

-- Brands
INSERT INTO Brands (brand_id, brand_name) VALUES (1, 'Coca-Cola');
INSERT INTO Brands (brand_id, brand_name) VALUES (2, 'PepsiCo');
INSERT INTO Brands (brand_id, brand_name) VALUES (3, 'Dairy Farms');

-- Product types
INSERT INTO Product_Types (product_type_id, type_name) VALUES (1, 'Beverages');
INSERT INTO Product_Types (product_type_id, type_name) VALUES (2, 'Dairy');
INSERT INTO Product_Types (product_type_id, type_name) VALUES (3, 'Bakery');

-- Vendors
INSERT INTO Vendors (
    vendor_id, vendor_name, phone, email, street_address, city, state, postal_code
) VALUES (
    1, 'Atlanta Beverage Supply', '404-555-0101',
    'orders@atlbev.example', '100 Supply Road', 'Atlanta', 'GA', '30303'
);

INSERT INTO Vendors (
    vendor_id, vendor_name, phone, email, street_address, city, state, postal_code
) VALUES (
    2, 'Georgia Dairy Distributors', '404-555-0102',
    'orders@gadairy.example', '200 Farm Lane', 'Decatur', 'GA', '30030'
);

-- Stores
INSERT INTO Stores (
    store_id, store_name, street_address, city, state, postal_code
) VALUES (
    1, 'Downtown Market', '10 Main Street', 'Atlanta', 'GA', '30303'
);

INSERT INTO Stores (
    store_id, store_name, street_address, city, state, postal_code
) VALUES (
    2, 'Northside Market', '25 Peachtree Road', 'Atlanta', 'GA', '30309'
);

-- Customers
INSERT INTO Customers (
    customer_id, first_name, last_name, email, phone,
    street_address, city, state, postal_code
) VALUES (
    1, 'Jordan', 'Lee', 'jordan.lee@example.com', '404-555-0201',
    '15 Oak Street', 'Atlanta', 'GA', '30303'
);

INSERT INTO Customers (
    customer_id, first_name, last_name, email, phone,
    street_address, city, state, postal_code
) VALUES (
    2, 'Morgan', 'Patel', 'morgan.patel@example.com', '404-555-0202',
    '22 Pine Avenue', 'Decatur', 'GA', '30030'
);

-- Products
INSERT INTO Products (
    product_id, product_name, brand_id, product_type_id, unit_price
) VALUES (1, 'Coca-Cola 12 oz Can', 1, 1, 1.25);

INSERT INTO Products (
    product_id, product_name, brand_id, product_type_id, unit_price
) VALUES (2, 'Pepsi 12 oz Can', 2, 1, 1.20);

INSERT INTO Products (
    product_id, product_name, brand_id, product_type_id, unit_price
) VALUES (3, 'Whole Milk 1 Gallon', 3, 2, 3.99);

INSERT INTO Products (
    product_id, product_name, brand_id, product_type_id, unit_price
) VALUES (4, 'White Bread Loaf', 3, 3, 2.49);

-- Inventory: current quantities by store and product
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (1, 1, 80);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (1, 2, 70);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (1, 3, 35);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (1, 4, 40);

INSERT INTO Inventory (store_id, product_id, quantity) VALUES (2, 1, 60);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (2, 2, 90);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (2, 3, 25);
INSERT INTO Inventory (store_id, product_id, quantity) VALUES (2, 4, 30);

-- Store sales
INSERT INTO Sales (sale_id, store_id, customer_id, sale_date)
VALUES (1, 1, 1, TIMESTAMP '2026-10-01 10:15:00');

INSERT INTO Sales (sale_id, store_id, customer_id, sale_date)
VALUES (2, 2, 2, TIMESTAMP '2026-10-02 14:30:00');

-- Items in each sale
INSERT INTO Sale_Items (sale_id, product_id, quantity, unit_price)
VALUES (1, 1, 2, 1.25);

INSERT INTO Sale_Items (sale_id, product_id, quantity, unit_price)
VALUES (1, 3, 1, 3.99);

INSERT INTO Sale_Items (sale_id, product_id, quantity, unit_price)
VALUES (2, 2, 3, 1.20);

INSERT INTO Sale_Items (sale_id, product_id, quantity, unit_price)
VALUES (2, 4, 1, 2.49);

-- Web orders
INSERT INTO Web_Orders (order_id, customer_id, order_date, order_status)
VALUES (1, 1, TIMESTAMP '2026-10-03 09:00:00', 'Pending');

INSERT INTO Web_Orders (order_id, customer_id, order_date, order_status)
VALUES (2, 2, TIMESTAMP '2026-10-04 11:30:00', 'Shipped');

-- Items in web orders
INSERT INTO Web_Order_Items (order_id, product_id, quantity, unit_price)
VALUES (1, 3, 1, 3.99);

INSERT INTO Web_Order_Items (order_id, product_id, quantity, unit_price)
VALUES (1, 4, 2, 2.49);

INSERT INTO Web_Order_Items (order_id, product_id, quantity, unit_price)
VALUES (2, 1, 4, 1.25);

-- Reorders sent to vendors
INSERT INTO Reorders (
    reorder_id, vendor_id, store_id, reorder_date, reorder_status
) VALUES (
    1, 1, 1, TIMESTAMP '2026-10-05 08:00:00', 'Ordered'
);

INSERT INTO Reorders (
    reorder_id, vendor_id, store_id, reorder_date, reorder_status
) VALUES (
    2, 2, 2, TIMESTAMP '2026-10-06 08:30:00', 'Pending'
);

-- Items included in reorders
INSERT INTO Reorder_Items (reorder_id, product_id, quantity)
VALUES (1, 1, 100);

INSERT INTO Reorder_Items (reorder_id, product_id, quantity)
VALUES (1, 2, 100);

INSERT INTO Reorder_Items (reorder_id, product_id, quantity)
VALUES (2, 3, 50);

-- Shipments for reorders
INSERT INTO Shipments (
    shipment_id, reorder_id, shipment_date, shipment_status
) VALUES (
    1, 1, TIMESTAMP '2026-10-08 13:00:00', 'Delivered'
);

INSERT INTO Shipments (
    shipment_id, reorder_id, shipment_date, shipment_status
) VALUES (
    2, 2, NULL, 'In Transit'
);

-- Products received in shipments
INSERT INTO Shipment_Items (shipment_id, product_id, quantity)
VALUES (1, 1, 100);

INSERT INTO Shipment_Items (shipment_id, product_id, quantity)
VALUES (1, 2, 100);

-- Save the inserted sample records.
COMMIT;