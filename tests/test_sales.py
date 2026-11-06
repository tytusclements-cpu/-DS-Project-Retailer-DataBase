import unittest
from database import get_connection


class TestSales(unittest.TestCase):

    def setUp(self):
        """Connect to the database before each test."""
        self.connection = get_connection()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        """Close the database connection after each test."""
        self.connection.rollback()
        self.cursor.close()
        self.connection.close()

    def test_sales_records_exist(self):
        """Check that sales records exist."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sales
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)

    def test_sale_items_exist(self):
        """Check that sale item records exist."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sale_Items
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)

    def test_sales_reference_valid_stores(self):
        """Check that every sale references an existing store."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sales s
            LEFT JOIN Stores st
                ON s.store_id = st.store_id
            WHERE st.store_id IS NULL
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_sales_reference_valid_customers(self):
        """Check that non-null customer IDs reference existing customers."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sales s
            LEFT JOIN Customers c
                ON s.customer_id = c.customer_id
            WHERE s.customer_id IS NOT NULL
              AND c.customer_id IS NULL
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_sale_item_quantities_are_positive(self):
        """Check that all sale item quantities are greater than zero."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sale_Items
            WHERE quantity <= 0
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_sale_item_prices_are_nonnegative(self):
        """Check that sale item prices are not negative."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sale_Items
            WHERE unit_price < 0
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_sales_have_sale_items(self):
        """Check that each sale has at least one sale item."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Sales s
            WHERE NOT EXISTS (
                SELECT 1
                FROM Sale_Items si
                WHERE si.sale_id = s.sale_id
            )
        """)

        empty_sales = self.cursor.fetchone()[0]

        self.assertEqual(empty_sales, 0)


if __name__ == "__main__":
    unittest.main()
