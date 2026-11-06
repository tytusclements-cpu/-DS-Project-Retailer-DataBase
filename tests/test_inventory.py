import unittest
from database import get_connection


class TestInventory(unittest.TestCase):

    def setUp(self):
        """Connect to the database before each test."""
        self.connection = get_connection()
        self.cursor = self.connection.cursor()

    def tearDown(self):
        """Close the database connection after each test."""
        self.connection.rollback()
        self.cursor.close()
        self.connection.close()

    def test_inventory_records_exist(self):
        """Check that inventory records exist."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Inventory
        """)

        count = self.cursor.fetchone()[0]

        self.assertGreater(count, 0)

    def test_inventory_quantity_not_negative(self):
        """Check that inventory quantities are not negative."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Inventory
            WHERE quantity < 0
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_inventory_product_exists(self):
        """Check that inventory records reference valid products."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Inventory i
            LEFT JOIN Products p
                ON i.product_id = p.product_id
            WHERE p.product_id IS NULL
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_inventory_store_exists(self):
        """Check that inventory records reference valid stores."""
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM Inventory i
            LEFT JOIN Stores s
                ON i.store_id = s.store_id
            WHERE s.store_id IS NULL
        """)

        invalid_count = self.cursor.fetchone()[0]

        self.assertEqual(invalid_count, 0)

    def test_inventory_update(self):
        """Check that an inventory quantity can be updated."""
        self.cursor.execute("""
            SELECT store_id, product_id, quantity
            FROM Inventory
            WHERE ROWNUM = 1
        """)

        record = self.cursor.fetchone()

        self.assertIsNotNone(record, "No inventory records found.")

        store_id, product_id, original_quantity = record
        new_quantity = original_quantity + 1

        self.cursor.execute("""
            UPDATE Inventory
            SET quantity = :new_quantity
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {
            "new_quantity": new_quantity,
            "store_id": store_id,
            "product_id": product_id
        })

        self.cursor.execute("""
            SELECT quantity
            FROM Inventory
            WHERE store_id = :store_id
              AND product_id = :product_id
        """, {
            "store_id": store_id,
            "product_id": product_id
        })

        updated_quantity = self.cursor.fetchone()[0]

        self.assertEqual(updated_quantity, new_quantity)


if __name__ == "__main__":
    unittest.main()
