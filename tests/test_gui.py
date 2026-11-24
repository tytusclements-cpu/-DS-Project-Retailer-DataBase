"""
Tests for the reusable parts of the graphical interface (form validation,
tables, drop-downs). They need a display but no database, and skip
themselves where no display is available (for example on a CI server).
"""

import tkinter as tk
import unittest
from decimal import Decimal

from gui_dialogs import FieldGrid
from gui_theme import apply_theme
from gui_widgets import ChoiceBox, DataTable


class TkTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
        except tk.TclError as error:
            raise unittest.SkipTest(f"no display available: {error}")

        cls.root.withdraw()
        apply_theme(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()


def fill(grid, key, text):
    widget = grid.widgets[key]

    if isinstance(widget, ChoiceBox):
        widget.set(text)
    else:
        widget.variable.set(text)


class TestFieldGrid(TkTestCase):

    def make(self, *fields):
        return FieldGrid(self.root, list(fields))

    def test_required_text_is_checked(self):
        grid = self.make({"key": "name", "label": "Name"})

        values, ok = grid.validate()

        self.assertFalse(ok)
        self.assertIn("required", grid._errors["name"].cget("text"))

    def test_optional_blank_becomes_none(self):
        grid = self.make({"key": "note", "label": "Note", "required": False})

        values, ok = grid.validate()

        self.assertTrue(ok)
        self.assertIsNone(values["note"])

    def test_text_is_trimmed_and_limited(self):
        grid = self.make({"key": "name", "label": "Name", "max_len": 5})

        fill(grid, "name", "  abc  ")
        self.assertEqual(grid.validate()[0]["name"], "abc")

        fill(grid, "name", "abcdefg")
        self.assertFalse(grid.validate()[1])

    def test_validator_message_is_shown(self):
        grid = self.make({
            "key": "email", "label": "Email",
            "validator": lambda text: "@" in text, "error": "Need an @."
        })

        fill(grid, "email", "nope")
        _, ok = grid.validate()

        self.assertFalse(ok)
        self.assertEqual(grid._errors["email"].cget("text"), "Need an @.")

    def test_int_bounds(self):
        grid = self.make({"key": "qty", "label": "Qty", "kind": "int",
                          "minimum": 1, "maximum": 10})

        for bad in ("abc", "1.5", "0", "11"):
            fill(grid, "qty", bad)
            self.assertFalse(grid.validate()[1], bad)

        fill(grid, "qty", "7")
        self.assertEqual(grid.validate()[0]["qty"], 7)

    def test_money_rules(self):
        grid = self.make({"key": "price", "label": "Price", "kind": "money"})

        for bad in ("x", "-1", "1.234", "NaN", "999999999"):
            fill(grid, "price", bad)
            self.assertFalse(grid.validate()[1], bad)

        fill(grid, "price", "$1,234.50")
        self.assertEqual(grid.validate()[0]["price"], Decimal("1234.50"))

    def test_choice_returns_id(self):
        grid = self.make({
            "key": "store", "label": "Store", "kind": "choice",
            "choices": [(1, "North"), (2, "South")],
        })

        fill(grid, "store", "south")
        self.assertEqual(grid.validate()[0]["store"], 2)

        fill(grid, "store", "East")
        self.assertFalse(grid.validate()[1])

    def test_editable_choice_accepts_new_text(self):
        grid = self.make({
            "key": "brand", "label": "Brand", "kind": "choice",
            "choices": [(1, "Acme")], "editable": True,
        })

        fill(grid, "brand", "acme")
        self.assertEqual(grid.validate()[0]["brand"], 1)

        fill(grid, "brand", "Brand New")
        self.assertEqual(grid.validate()[0]["brand"], "Brand New")

    def test_blank_choice_is_none(self):
        grid = self.make({
            "key": "customer", "label": "Customer", "kind": "choice",
            "choices": [(1, "Ava")], "required": False, "blank": "Anonymous",
        })

        values, ok = grid.validate()

        self.assertTrue(ok)
        self.assertIsNone(values["customer"])


class TestDataTable(TkTestCase):

    COLUMNS = [("ID", 50, "e"), ("Name", 120), ("Price", 80, "e")]
    ROWS = [(1, "Bread", "$10.00"), (2, "apple", "$9.50"),
            (3, "Cheese", "$1,200.00")]

    def make(self, **options):
        table = DataTable(self.root, self.COLUMNS, **options)
        table.set_rows(self.ROWS)
        return table

    def shown(self, table):
        return [table.tree.item(i)["values"][1]
                for i in table.tree.get_children()]

    def test_shows_all_rows(self):
        self.assertEqual(len(self.make().tree.get_children()), 3)

    def test_filter_is_case_insensitive_across_columns(self):
        table = self.make()

        table.set_filter("CHEESE")
        self.assertEqual(self.shown(table), ["Cheese"])

        table.set_filter("9.50")
        self.assertEqual(self.shown(table), ["apple"])

        table.set_filter("")
        self.assertEqual(len(self.shown(table)), 3)

    def test_money_sorts_numerically(self):
        table = self.make()

        table._sort_by(2)
        self.assertEqual(self.shown(table), ["apple", "Bread", "Cheese"])

        table._sort_by(2)
        self.assertEqual(self.shown(table), ["Cheese", "Bread", "apple"])

    def test_text_sorts_ignoring_case(self):
        table = self.make()

        table._sort_by(1)
        self.assertEqual(self.shown(table), ["apple", "Bread", "Cheese"])

    def test_selection_survives_new_data(self):
        selected = []
        table = self.make(on_select=selected.append)

        self.assertTrue(table.select_key((2,)))
        self.root.update()
        self.assertEqual(table.selected()[1], "apple")

        table.set_rows([(3, "Cheese", "$1.00"), (2, "apple", "$2.00")])
        self.assertEqual(table.selected()[2], "$2.00")

    def test_selection_cleared_when_row_disappears(self):
        table = self.make()
        table.select_key((1,))
        self.root.update()

        table.set_rows([(2, "apple", "$9.50")])

        self.assertIsNone(table.selected())


class TestChoiceBox(TkTestCase):

    def test_blank_label_means_none(self):
        box = ChoiceBox(self.root, [(1, "A")], blank="All")

        self.assertEqual(box.get(), "All")
        self.assertIsNone(box.value())

    def test_set_value_selects_label(self):
        box = ChoiceBox(self.root, [(1, "A"), (2, "B")])

        box.set_value(2)

        self.assertEqual(box.get(), "B")
        self.assertEqual(box.value(), 2)

    def test_unknown_text_is_an_error_unless_editable(self):
        strict = ChoiceBox(self.root, [(1, "A")])
        strict.set("zzz")

        with self.assertRaises(ValueError):
            strict.value()

        loose = ChoiceBox(self.root, [(1, "A")], editable=True)
        loose.set("zzz")

        self.assertEqual(loose.value(), "zzz")


if __name__ == "__main__":
    unittest.main()
