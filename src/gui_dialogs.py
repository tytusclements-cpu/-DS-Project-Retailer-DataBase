# gui_dialogs.py
# Modal dialogs: generic forms, the "shopping cart" used for sales and
# orders, and the database connection dialog.

import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk

from cli_utils import money
from gui_theme import C, px
from gui_widgets import ChoiceBox, DataTable

MAX_ITEM_QUANTITY = 1_000_000


# --------------------------------------------------
# MODAL BASE
# --------------------------------------------------

class ModalDialog(tk.Toplevel):
    """A centred window that blocks the app until it is closed."""

    def __init__(self, parent, title):
        super().__init__(parent.winfo_toplevel())

        self.withdraw()
        self.title(title)
        self.configure(bg=C["surface"])
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)

        self.result = None

        self.body = ttk.Frame(self, style="Card.TFrame", padding=(26, 22, 26, 8))
        self.body.pack(fill="both", expand=True)

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        self.footer = ttk.Frame(self, style="Alt.TFrame", padding=(26, 12))
        self.footer.pack(fill="x")

        self.bind("<Escape>", lambda _e: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def add_buttons(self, submit_text, submit_command, cancel_text="Cancel"):
        self.submit_button = ttk.Button(
            self.footer, text=submit_text, style="Accent.TButton",
            command=submit_command
        )
        self.submit_button.pack(side="right")

        ttk.Button(
            self.footer, text=cancel_text, command=self.cancel
        ).pack(side="right", padx=(0, 8))

    def present(self):
        self.update_idletasks()

        parent = self.master
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 3

        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()

        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

        self.focus_set()

    def cancel(self):
        self.result = None
        self.close()

    def close(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass

        self.destroy()

    def show(self):
        """Run the dialog and return its result (None if cancelled)."""

        self.present()
        self.wait_window(self)
        return self.result


# --------------------------------------------------
# FIELD GRID
# --------------------------------------------------

class FieldGrid(ttk.Frame):
    """
    Labelled inputs with inline validation.

    Each field is a dict:
        key, label, kind ("text", "int", "money", "choice")
        required (default True), value (initial), hint
        text:   max_len, validator, error, secret
        int:    minimum, maximum
        choice: choices [(id, label)], editable, blank
        wide:   span all columns
    """

    def __init__(self, parent, fields, columns=1, field_width=34):
        super().__init__(parent, style="Card.TFrame")

        self.fields = fields
        self.widgets = {}
        self._errors = {}

        for column in range(columns):
            self.columnconfigure(column, weight=1)

        row = column = 0

        for spec in fields:
            wide = spec.get("wide") or columns == 1

            if wide and column != 0:
                row, column = row + 1, 0

            cell = ttk.Frame(self, style="Card.TFrame")
            cell.grid(
                row=row, column=column, sticky="new",
                columnspan=columns if wide else 1,
                padx=(0, 16) if (not wide and column < columns - 1) else 0,
                pady=(0, 12)
            )

            required = spec.get("required", True)
            label = spec["label"] + (" *" if required else "")
            ttk.Label(cell, text=label.upper(), style="Field.TLabel").pack(
                anchor="w", pady=(0, 4)
            )

            widget = self._make_widget(cell, spec, field_width)
            widget.pack(fill="x")
            self.widgets[spec["key"]] = widget

            if spec.get("hint"):
                ttk.Label(
                    cell, text=spec["hint"], style="Hint.TLabel",
                    wraplength=px(300), justify="left"
                ).pack(anchor="w", pady=(3, 0))

            error = ttk.Label(
                cell, text="", style="Error.TLabel", wraplength=px(300),
                justify="left"
            )
            error.pack(anchor="w")
            self._errors[spec["key"]] = error

            if wide:
                row, column = row + 1, 0
            else:
                column += 1

                if column >= columns:
                    row, column = row + 1, 0

    def _make_widget(self, parent, spec, width):
        if spec.get("kind") == "choice":
            box = ChoiceBox(
                parent, spec.get("choices", ()),
                editable=spec.get("editable", False),
                blank=spec.get("blank"), width=width
            )

            if spec.get("value") is not None:
                box.set_value(spec["value"])

            return box

        initial = spec.get("value")
        variable = tk.StringVar(value="" if initial is None else str(initial))
        entry = ttk.Entry(
            parent, textvariable=variable, width=width,
            show="•" if spec.get("secret") else ""
        )
        entry.variable = variable

        return entry

    # ---------- reading ----------

    def _read(self, spec):
        widget = self.widgets[spec["key"]]
        required = spec.get("required", True)
        kind = spec.get("kind", "text")

        if kind == "choice":
            value = widget.value()

            if value is None and required:
                raise ValueError("This field is required.")

            return value

        text = widget.get().strip()

        if text == "":
            if required:
                raise ValueError("This field is required.")

            return None

        if kind == "int":
            try:
                number = int(text)
            except ValueError:
                raise ValueError("Enter a whole number.")

            minimum, maximum = spec.get("minimum"), spec.get("maximum")

            if minimum is not None and number < minimum:
                raise ValueError(f"Must be at least {minimum:,}.")

            if maximum is not None and number > maximum:
                raise ValueError(f"Must be at most {maximum:,}.")

            return number

        if kind == "money":
            try:
                amount = Decimal(text.replace("$", "").replace(",", ""))
            except InvalidOperation:
                raise ValueError("Enter a valid amount, for example 3.99.")

            if not amount.is_finite():
                raise ValueError("Enter a valid amount, for example 3.99.")

            if amount < 0:
                raise ValueError("Amount cannot be negative.")

            if amount != amount.quantize(Decimal("0.01")):
                raise ValueError("Use at most two decimal places.")

            if amount > Decimal("99999999.99"):
                raise ValueError("Amount is too large.")

            return amount

        max_len = spec.get("max_len")

        if max_len is not None and len(text) > max_len:
            raise ValueError(f"Use at most {max_len} characters.")

        validator = spec.get("validator")

        if validator is not None and not validator(text):
            raise ValueError(spec.get("error", "Invalid value."))

        return text

    def validate(self):
        """Return (values, ok). Problems are shown beside each field."""

        values, first_bad = {}, None

        for spec in self.fields:
            key = spec["key"]

            try:
                values[key] = self._read(spec)
                self._errors[key].configure(text="")
            except ValueError as error:
                self._errors[key].configure(text=str(error))
                first_bad = first_bad or self.widgets[key]

        if first_bad is not None:
            first_bad.focus_set()

        return values, first_bad is None

    def focus_first(self):
        if self.fields:
            self.widgets[self.fields[0]["key"]].focus_set()


# --------------------------------------------------
# FORM DIALOG
# --------------------------------------------------

class FormDialog(ModalDialog):
    """Ask for a set of values. show() returns {key: value} or None."""

    def __init__(self, parent, title, fields, submit="Save", intro=None,
                 columns=1):
        super().__init__(parent, title)

        if intro:
            ttk.Label(
                self.body, text=intro, style="CardMuted.TLabel",
                wraplength=px(420), justify="left"
            ).pack(anchor="w", pady=(0, 14))

        self.grid_fields = FieldGrid(
            self.body, fields, columns=columns,
            field_width=26 if columns > 1 else 40
        )
        self.grid_fields.pack(fill="both", expand=True)

        self.add_buttons(submit, self._submit)
        self.bind("<Return>", lambda _e: self._submit())

        self.after(50, self.grid_fields.focus_first)

    def _submit(self):
        values, ok = self.grid_fields.validate()

        if ok:
            self.result = values
            self.close()


# --------------------------------------------------
# CART DIALOG
# --------------------------------------------------

class CartDialog(ModalDialog):
    """
    Build a list of products and quantities (a sale, an online order or a
    vendor reorder).

    header_fields: FieldGrid fields asked for above the cart.
    load_products(driver_value) -> [(product_id, name, price, stock)]
        runs in a worker thread; `driver` names the header field whose value
        it needs (None = load once at start).
    show_price / show_stock control the extra columns and the stock limit.

    show() returns {"header": {...}, "lines": {product_id: quantity}}.
    """

    def __init__(self, parent, app, title, header_fields, load_products,
                 driver=None, show_price=True, show_stock=False,
                 submit="Complete", header_columns=2):
        super().__init__(parent, title)

        self.app = app
        self._load_products = load_products
        self._driver = driver
        self._driver_value = None
        self._show_price = show_price
        self._show_stock = show_stock
        self._products = {}         # id -> (name, price, stock)
        self._cart = {}             # id -> quantity

        self.header = FieldGrid(
            self.body, header_fields, columns=header_columns, field_width=28
        )
        self.header.pack(fill="x")

        if driver is not None:
            box = self.header.widgets[driver]
            box.bind("<<ComboboxSelected>>", self._driver_changed)
            box.bind("<FocusOut>", self._driver_changed)

        self._build_picker()
        self._build_cart()
        self._build_footer(submit)

        if driver is None:
            self._reload_products(None)
        else:
            self._say("Choose a store first to see what it has in stock.")

        self.after(50, self.header.focus_first)

    # ---------- layout ----------

    def _build_picker(self):
        ttk.Label(
            self.body, text="ADD PRODUCTS", style="Field.TLabel"
        ).pack(anchor="w", pady=(4, 6))

        row = ttk.Frame(self.body, style="Card.TFrame")
        row.pack(fill="x")

        self.picker = ChoiceBox(row, width=46)
        self.picker.pack(side="left", fill="x", expand=True)

        self.quantity = ttk.Spinbox(
            row, from_=1, to=MAX_ITEM_QUANTITY, width=7
        )
        self.quantity.set("1")
        self.quantity.pack(side="left", padx=8)

        ttk.Button(row, text="Add", command=self._add).pack(side="left")

        self.picker.bind("<Return>", lambda _e: self._add())
        self.quantity.bind("<Return>", lambda _e: self._add())

        self.picker_message = ttk.Label(
            self.body, text="", style="Hint.TLabel", wraplength=px(560),
            justify="left"
        )
        self.picker_message.pack(anchor="w", pady=(4, 8))

    def _build_cart(self):
        columns = [("ID", 55, "e"), ("Product", 250, "w", True),
                   ("Qty", 60, "e")]

        if self._show_price:
            columns += [("Price", 90, "e"), ("Subtotal", 100, "e")]

        self.table = DataTable(
            self.body, columns, compact=True, footer=False, height=7,
            on_select=self._cart_selected, empty_text="No products added yet"
        )
        self.table.pack(fill="both", expand=True)

        tools = ttk.Frame(self.body, style="Card.TFrame")
        tools.pack(fill="x", pady=(8, 0))

        self.remove_button = ttk.Button(
            tools, text="Remove selected", command=self._remove,
            state="disabled"
        )
        self.remove_button.pack(side="left")

        self.total_label = ttk.Label(tools, text="", style="Total.TLabel")
        self.total_label.pack(side="right")

    def _build_footer(self, submit):
        self.add_buttons(submit, self._submit)
        self._refresh_cart()

    # ---------- products ----------

    def _say(self, text, error=False):
        self.picker_message.configure(
            text=text, foreground=C["danger"] if error else C["faint"]
        )

    def _driver_changed(self, _event=None):
        try:
            value = self.header.widgets[self._driver].value()
        except ValueError:
            value = None

        if value == self._driver_value:
            return

        self._driver_value = value
        self._reload_products(value)

    def _reload_products(self, driver_value):
        self._products = {}
        self.picker.set("")
        self.picker.set_choices([])

        if self._driver is not None and driver_value is None:
            self._say("Choose a store first to see what it has in stock.")
            return

        self._say("Loading products…")
        token = self._driver_value

        def done(products):
            if not self.winfo_exists() or token != self._driver_value:
                return

            self._set_products(products)

        self.app.run(lambda: self._load_products(driver_value), done)

    def _set_products(self, products):
        self._products = {pid: (name, price, stock)
                          for pid, name, price, stock in products}

        choices = []

        for pid, name, price, stock in products:
            label = name

            if self._show_price:
                label += f"  ·  {money(price)}"

            if self._show_stock:
                label += f"  ·  {stock} in stock"

            choices.append((pid, label))

        self.picker.set_choices(choices)
        self._say("" if products else "No products available.")

    # ---------- cart ----------

    def _add(self):
        try:
            product_id = self.picker.value()
        except ValueError:
            product_id = None

        if product_id is None or product_id not in self._products:
            self._say("Pick a product from the list first.", error=True)
            return

        try:
            quantity = int(self.quantity.get())

            if not 1 <= quantity <= MAX_ITEM_QUANTITY:
                raise ValueError
        except ValueError:
            self._say(
                f"Quantity must be a whole number from 1 to "
                f"{MAX_ITEM_QUANTITY:,}.", error=True
            )
            return

        name, _price, stock = self._products[product_id]
        wanted = self._cart.get(product_id, 0) + quantity

        if self._show_stock and wanted > stock:
            self._say(
                f"Only {stock} of {name} in stock "
                f"({self._cart.get(product_id, 0)} already added).",
                error=True
            )
            return

        self._cart[product_id] = wanted
        self._say("")
        self.picker.set("")
        self.picker.reset_filter()
        self.quantity.set("1")
        self.picker.focus_set()
        self._refresh_cart()

    def _remove(self):
        selected = self.table.selected()

        if selected is not None:
            self._cart.pop(selected[0], None)
            self._refresh_cart()

    def _cart_selected(self, values):
        self.remove_button.configure(
            state="normal" if values is not None else "disabled"
        )

    def _refresh_cart(self):
        rows, total, units = [], 0, 0

        for pid, quantity in self._cart.items():
            name, price, _stock = self._products[pid]
            units += quantity

            if self._show_price:
                total += price * quantity
                rows.append((pid, name, quantity, money(price),
                             money(price * quantity)))
            else:
                rows.append((pid, name, quantity))

        self.table.set_rows(rows)

        if self._show_price:
            self.total_label.configure(text=f"Total  {money(total)}")
        else:
            self.total_label.configure(
                text=f"{units:,} unit{'s' if units != 1 else ''}"
            )

        # The product list depends on the driver, so lock it once used.
        if self._driver is not None:
            self.header.widgets[self._driver].configure(
                state="disabled" if self._cart else "normal"
            )

    def _submit(self):
        header, ok = self.header.validate()

        if not ok:
            return

        if not self._cart:
            self._say("Add at least one product.", error=True)
            return

        self.result = {"header": header, "lines": dict(self._cart)}
        self.close()


# --------------------------------------------------
# CONNECTION DIALOG
# --------------------------------------------------

class ConnectDialog(ModalDialog):
    """
    Ask for Oracle connection details and test them.
    `connect(settings)` runs in a worker thread and raises on failure.
    show() returns the working settings dict, or None if cancelled.
    """

    def __init__(self, parent, app, settings, connect, message=None):
        super().__init__(parent, "Connect to database")

        self.app = app
        self._connect = connect

        ttk.Label(
            self.body, text="Retailer Database", style="CardTitle.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            self.body,
            text=message or "Enter the details of your Oracle database.",
            style="CardMuted.TLabel", wraplength=px(420), justify="left"
        ).pack(anchor="w", pady=(2, 16))

        self.grid_fields = FieldGrid(self.body, [
            {"key": "user", "label": "User", "value": settings["user"],
             "max_len": 128},
            {"key": "password", "label": "Password",
             "value": settings["password"], "secret": True,
             "required": False},
            {"key": "host", "label": "Host", "value": settings["host"],
             "max_len": 255},
            {"key": "port", "label": "Port", "kind": "int",
             "value": settings["port"], "minimum": 1, "maximum": 65535},
            {"key": "service", "label": "Service name",
             "value": settings["service"], "max_len": 128, "wide": True},
        ], columns=2, field_width=22)
        self.grid_fields.pack(fill="x")

        self.status = ttk.Label(
            self.body, text="", style="Error.TLabel", wraplength=px(420),
            justify="left"
        )
        self.status.pack(anchor="w", pady=(0, 8))

        self.add_buttons("Connect", self._submit, cancel_text="Quit")
        self.bind("<Return>", lambda _e: self._submit())
        self.after(50, self.grid_fields.focus_first)

    def _submit(self):
        values, ok = self.grid_fields.validate()

        if not ok:
            return

        values["password"] = values["password"] or ""

        self.submit_button.configure(state="disabled", text="Connecting…")
        self.status.configure(text="")

        def success(_result):
            if self.winfo_exists():
                self.result = values
                self.close()

        def failure(error):
            if not self.winfo_exists():
                return

            self.submit_button.configure(state="normal", text="Connect")
            first_line = (str(error).strip().splitlines() or [""])[0]
            self.status.configure(
                text=f"Could not connect: {first_line or 'unknown error'}"
            )

        self.app.run(lambda: self._connect(values), success, failure)
