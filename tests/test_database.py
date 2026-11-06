import unittest
from database import get_connection


class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Connect to the Oracle database before each test."""
        self.connection = get_connection()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        """Close the database connection after each test."""
        self.cursor.close()
        self.connection.close()

    def test_database_connection(self):
        """Check that the database connection works."""
        self.cursor.execute("SELECT 1 FROM DUAL")
        result = self.cursor.fetchone()

        self.assertEqual(result[0], 1)

    def test_required_tables_exist(self):
        """Check that all required database tables exist."""
        required_tables = [
            "BRANDS",
            "PRODUCT_TYPES",
            "VENDORS",
            "STORES",
            "CUSTOMERS",
            "PRODUCTS",
            "INVENTORY",
            "SALES",
            "SALE_ITEMS",
            "WEB_ORDERS",
            "WEB_ORDER_ITEMS",
            "REORDERS",
            "REORDER_ITEMS",
            "SHIPMENTS",
            "SHIPMENT_ITEMS"
        ]

        self.cursor.execute("""
            SELECT TABLE_NAME
            FROM USER_TABLES
        """)

        existing_tables = {
            row[0] for row in self.cursor.fetchall()
        }

        for table in required_tables:
            with self.subTest(table=table):
                self.assertIn(
                    table,
                    existing_tables,
                    f"Missing database table: {table}"
                )

    def test_products_table_has_data(self):
        """Check that the Products table contains records."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Products
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)

    def test_stores_table_has_data(self):
        """Check that the Stores table contains records."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Stores
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)

    def test_customers_table_has_data(self):
        """Check that the Customers table contains records."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Customers
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()
