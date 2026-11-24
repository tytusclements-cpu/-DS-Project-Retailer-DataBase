# -DS-Project-Retailer-DataBase

## CSC4710 – Database Systems Project

**Project Name:** Retailer Database Management System  
**Team Members:** Tytus Clements and Quang Tran

---

## 1. Project Overview

The Retailer Database Management System is designed to manage the daily operations of a retail business. The system uses an Oracle relational database to store and organize information about products, brands, vendors, stores, customers, inventory, sales, online orders, reorders, and shipments.

A Python application provides an interface for managing database records and performing common retail operations.

The project demonstrates relational database design, SQL queries, database constraints, transactions, and concurrent database access.

## 2. Project Objectives

The main objectives are to:

- Design a relational database for a retail business.
- Create an Entity-Relationship (ER) diagram.
- Develop a relational schema with primary and foreign keys.
- Implement database tables, constraints, and indexes.
- Populate the database with sample data.
- Develop a Python application that interacts with the database.
- Generate reports using SQL queries.
- Test database transactions and concurrent inventory operations.

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.12 | Application development |
| Oracle Database | Database management |
| Oracle SQL Developer | SQL development and database management |
| Python `oracledb` | Python-to-Oracle connectivity |
| SQL | Database queries and operations |
| GitHub | Version control and collaboration |

## 4. Project Structure

```text
DS-Project-Retailer-DataBase/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── docs/
│   ├── project_plan.md
│   ├── ER_Diagram.png
│   └── relational_schema.pdf
│
├── database/
│   ├── 01_create_tables.sql
│   ├── 02_create_constraints.sql
│   ├── 03_create_indexes.sql
│   ├── 04_insert_sample_data.sql
│   └── 05_test_queries.sql
│
├── src/
│   ├── main.py
│   ├── database.py
│   ├── products.py
│   ├── stores.py
│   ├── inventory.py
│   ├── customers.py
│   ├── sales.py
│   ├── orders.py
│   ├── vendors.py
│   ├── reports.py
│   ├── gui.py
│   └── gui_*.py
│
├── tests/
│   ├── test_database.py
│   ├── test_inventory.py
│   ├── test_sales.py
│   ├── test_gui.py
│   └── test_concurrency.py
│
└── data/
    └── sample_data.csv
```

## 5. Database Design

The database contains 15 relational tables:

| Table | Description |
|---|---|
| Brands | Stores product brand information |
| Product_Types | Stores product categories |
| Products | Stores product information and prices |
| Vendors | Stores vendor contact information |
| Stores | Stores retail store information |
| Customers | Stores customer information |
| Inventory | Tracks product quantities at each store |
| Sales | Stores in-store sales transactions |
| Sale_Items | Stores products included in each sale |
| Web_Orders | Stores customer online orders |
| Web_Order_Items | Stores products included in online orders |
| Reorders | Stores inventory reorder information |
| Reorder_Items | Stores products included in reorders |
| Shipments | Tracks shipments associated with reorders |
| Shipment_Items | Stores products included in shipments |

The database uses primary keys, foreign keys, composite keys, unique constraints, and check constraints to maintain data integrity.

## 6. Application Features

The Python application provides the following functionality:

### Product Management
- Add products.
- View products.
- Update product information.
- Delete products.
- Search for products.

### Store Management
- Add stores.
- View stores.
- Update store information.
- Delete stores.
- Search for stores.

### Inventory Management
- View store inventory.
- Search inventory.
- Add inventory records.
- Update product quantities.
- Delete inventory records.

### Customer Management
- Add customers.
- View customers.
- Update customer information.
- Delete customers.
- Search customers.

### Sales Management
- Create sales transactions.
- Add products to sales.
- View sales records.
- View individual sale details.
- Search sales by store.
- Update inventory when products are sold.

### Online Order Management
- Create online orders.
- View orders.
- View order details.
- Add products to orders.
- Update order statuses.
- Delete orders.

### Vendor Management
- Add vendors.
- View vendors.
- Update vendor information.
- Delete vendors.
- Search vendors.
- View vendor reorder history.

### Reports
The reporting module provides SQL reports for:

- Top 20 products sold by store.
- Top 5 stores by sales revenue.
- Coca-Cola versus Pepsi sales comparisons.
- Products purchased with milk.
- Inventory reports.
- Customer sales history.
- Online order reports.
- Vendor reorder reports.
- Shipment reports.

## 7. Installation and Setup

### Requirements

Before running the application, install:

- Python 3.12
- Oracle Database
- Oracle SQL Developer (recommended)
- Python Oracle database driver

### Step 1: Clone the Repository

```bash
git clone https://github.com/tytusclements-cpu/-DS-Project-Retailer-DataBase.git
```

Navigate into the project directory:

```bash
cd DS-Project-Retailer-DataBase
```

### Step 2: Install Dependencies

Install the Python Oracle driver:

```bash
py -m pip install -r requirements.txt
```

If the requirements file does not include it, install it separately:

```bash
py -m pip install oracledb
```

### Step 3: Configure the Database Connection

Open:

```text
src/database.py
```

Update the database connection settings:

```python
DB_USER = "your_username"
DB_PASSWORD = "your_password"
DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE = "your_service_name"
```

Replace the example values with your Oracle database credentials and service name.

### Step 4: Create the Database Tables

Open Oracle SQL Developer and connect to your Oracle database.

Execute the SQL scripts in this order:

1. `01_create_tables.sql`
2. `02_create_constraints.sql`
3. `03_create_indexes.sql`
4. `04_insert_sample_data.sql`
5. `05_test_queries.sql`

The scripts create the database structure, apply constraints and indexes, insert sample data, and provide test queries.

### Step 5: Test the Database Connection

From the project root directory, run:

```bash
py -c "import sys; sys.path.insert(0, 'src'); from database import test_connection; print(test_connection())"
```

Make sure the Oracle database and listener services are running before testing.

### Step 6: Start the Application

Run:

```bash
py src/main.py
```

The application will display the main menu.

### Step 7: Start the Graphical Interface (Optional)

The same system is also available as a desktop application built with Tkinter, which is included with Python. No extra packages are required.

```bash
py src/gui.py
```

The graphical interface provides a dashboard and screens for products, stores, customers, vendors, inventory, sales, online orders, vendor reorders, and reports.

- Click a column heading to sort a table. Use the **Search** box to filter the rows shown.
- Select a row to see its details. Double-click a row to edit it.
- New sales, online orders, and reorders open a product picker. A sale only offers products that the selected store has in stock.
- Reports can be exported to CSV.
- Keyboard shortcuts: **F5** refreshes, **Ctrl+F** moves to search, and **Ctrl+1** to **Ctrl+8** switch screens.

If the application cannot connect to the database, a sign-in window asks for the user, password, host, port, and service name. **Change connection** in the sidebar switches databases later. The console application and the graphical interface use the same database code and can be used side by side.

## 8. Running Tests

Run the database tests:

```bash
py -m unittest discover -s tests -v
```

Run individual tests:

```bash
py -m unittest tests.test_database -v
```

```bash
py -m unittest tests.test_inventory -v
```

```bash
py -m unittest tests.test_sales -v
```

Run the graphical interface tests. These need a display but no database:

```bash
py -m unittest tests.test_gui -v
```

Run the concurrency test:

```bash
py -m tests.test_concurrency
```

**Note:** The concurrency test changes inventory quantities in the database. Use test data and restore the original inventory quantities when finished.

## 9. Concurrency Testing

The concurrency test simulates multiple users attempting to purchase the same product at the same store.

The test uses Oracle transactions and row-level locking with `SELECT ... FOR UPDATE` to prevent multiple users from incorrectly purchasing the same available inventory.

This demonstrates how the database handles simultaneous inventory operations while maintaining data consistency.

## 10. Team Responsibilities

| Team Member | Responsibilities |
|---|---|
| Tytus Clements | Database design, SQL scripts, constraints, indexes, sample data, reports, and database testing |
| Quang Tran | Python application development, application interfaces, and functional testing |

Both team members contribute to database integration, project documentation, testing, and final project review.

## 11. Project Deliverables

The final project includes:

- Entity-Relationship diagram.
- Relational database schema.
- Oracle database creation scripts.
- Database constraints and indexes.
- Sample database records.
- SQL queries and reports.
- Python application source code.
- Database and application tests.
- Project documentation and setup instructions.

## 12. Conclusion

The Retailer Database Management System demonstrates how a relational database can support the operations of a retail business.

By combining Oracle Database, SQL, and Python, the project provides a structured solution for managing products, inventory, customers, sales, online orders, vendors, reorders, and shipments.

The project also demonstrates database integrity, transaction management, SQL reporting, and concurrency control.

---

**Course:** CSC4710 – Database Systems  
**Project:** Retailer Database Management System  
**Team Members:** Tytus Clements and Quang Tran
