# gui_base.py
# Shared page and panel classes used by every screen of the graphical
# interface, plus a few data helpers.

import tkinter as tk
from tkinter import messagebox, ttk

import oracledb

from cli_utils import UserError
from database import db_session
from gui_dialogs import FormDialog
from gui_theme import C
from gui_widgets import Card, DataTable, DetailPanel, SearchBox


# --------------------------------------------------
# DATA HELPERS
# --------------------------------------------------

# kind -> (SQL returning id + label, add "(#id)" to the label?)
CHOICE_SQL = {
    "stores": ("SELECT store_id, store_name FROM Stores "
               "ORDER BY store_name", True),
    "products": ("SELECT product_id, product_name FROM Products "
                 "ORDER BY product_name", True),
    "customers": ("SELECT customer_id, first_name || ' ' || last_name "
                  "FROM Customers ORDER BY last_name, first_name", True),
    "vendors": ("SELECT vendor_id, vendor_name FROM Vendors "
                "ORDER BY vendor_name", True),
    "brands": ("SELECT brand_id, brand_name FROM Brands "
               "ORDER BY brand_name", False),
    "types": ("SELECT product_type_id, type_name FROM Product_Types "
              "ORDER BY type_name", False),
}


def load_choices(cursor, *kinds):
    """Return {kind: [(id, label), ...]} for the drop-downs in a form."""

    result = {}

    for kind in kinds:
        sql, with_id = CHOICE_SQL[kind]
        cursor.execute(sql)

        result[kind] = [
            (row[0], f"{row[1]}  (#{row[0]})" if with_id else row[1])
            for row in cursor.fetchall()
        ]

    return result


# --------------------------------------------------
# PAGE
# --------------------------------------------------

class Page(ttk.Frame):
    """One screen: a title bar on top and content below."""

    title = ""
    subtitle = ""

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x", padx=28, pady=(24, 14))

        titles = ttk.Frame(header)
        titles.pack(side="left")
        ttk.Label(titles, text=self.title, style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(titles, text=self.subtitle, style="Subtitle.TLabel").pack(
            anchor="w", pady=(2, 0)
        )

        self.header_actions = ttk.Frame(header)
        self.header_actions.pack(side="right", anchor="s")

        ttk.Button(
            self.header_actions, text="Refresh", command=self.refresh
        ).pack(side="right")

        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True, padx=28, pady=(0, 24))

    def on_show(self):
        """Called every time the page is opened."""

        self.refresh()

    def refresh(self):
        """Reload the page's data."""

    def focus_search(self):
        """Move the cursor to the page's search box, if it has one."""


class PanelPage(Page):
    """A page that is just one list/detail panel."""

    panel_class = None

    def __init__(self, parent, app):
        super().__init__(parent, app)

        self.panel = self.panel_class(self.content, app)
        self.panel.pack(fill="both", expand=True)

    def refresh(self):
        self.panel.refresh()

    def focus_search(self):
        self.panel.search.focus()


# --------------------------------------------------
# LIST + DETAILS PANEL
# --------------------------------------------------

class ListDetail(ttk.Frame):
    """
    A searchable table with a details panel on the right.

    Subclasses provide:
        columns            DataTable columns
        fetch_rows()       worker thread: list of display-ready row tuples
        load_details(row)  worker thread: kwargs for DetailPanel.show()
        buttons()          [(text, command, ttk style, needs_selection)]
        build_filters(bar) optional extra widgets beside the search box
    """

    columns = []
    key_columns = (0,)
    empty_text = "No records found"
    detail_empty = "Select a row to see its details."
    detail_width = 360
    filters_inline = True      # False: filters get their own row

    def __init__(self, parent, app):
        super().__init__(parent)

        self.app = app
        self._token = 0
        self._load_token = 0
        self._need_selection = []
        self._pending_key = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = Card(self)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        self.toolbar = ttk.Frame(card, style="Card.TFrame", padding=(14, 12))
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.search = SearchBox(self.toolbar, self._filter)
        self.search.pack(side="left")

        if self.filters_inline:
            self.build_filters(self.toolbar)
        else:
            filter_bar = ttk.Frame(
                card, style="Card.TFrame", padding=(14, 0, 14, 12)
            )
            filter_bar.grid(row=1, column=0, sticky="ew")
            self.build_filters(filter_bar)

        for text, command, style, needs_selection in reversed(self.buttons()):
            button = ttk.Button(
                self.toolbar, text=text, command=command, style=style
            )
            button.pack(side="right", padx=(8, 0))

            if needs_selection:
                button.state(["disabled"])
                self._need_selection.append(button)

        tk.Frame(card, bg=C["border"], height=1).grid(row=2, column=0,
                                                       sticky="ew")

        self.table = DataTable(
            card, self.columns, on_select=self._selection_changed,
            on_activate=self.activate, key_columns=self.key_columns,
            empty_text=self.empty_text
        )
        self.table.grid(row=3, column=0, sticky="nsew")

        self.detail = None

        if self.detail_width:
            self.detail = DetailPanel(
                self, width=self.detail_width, empty=self.detail_empty
            )
            self.detail.grid(row=0, column=1, sticky="ns", padx=(16, 0))

    # ---------- hooks ----------

    def build_filters(self, bar):
        pass

    def buttons(self):
        return []

    def fetch_rows(self):
        raise NotImplementedError

    def row_tag(self, row):
        return None

    def after_load(self, rows):
        pass

    def load_details(self, row):
        return None

    def activate(self, row):
        """Double-click / Enter on a row."""

    # ---------- behaviour ----------

    def selected_id(self):
        row = self.table.selected()
        return None if row is None else int(row[0])

    def refresh(self, select_key=None):
        self._pending_key = select_key
        self._load_token += 1
        token = self._load_token

        self.app.run(self.fetch_rows, lambda rows: self._rows_loaded(token, rows))

    def _rows_loaded(self, token, rows):
        if token != self._load_token:
            return              # a newer refresh is on its way

        tags = [self.row_tag(row) for row in rows]
        self.table.set_rows(rows, tags=tags)
        self.after_load(rows)

        if self._pending_key is not None:
            self.table.select_key(self._pending_key)
            self._pending_key = None

    def _filter(self, text):
        self.table.set_filter(text)

    def _selection_changed(self, row):
        state = ["!disabled"] if row is not None else ["disabled"]

        for button in self._need_selection:
            button.state(state)

        if self.detail is None:
            return

        self._token += 1
        token = self._token

        if row is None:
            self.detail.clear()
            return

        def done(details):
            if token != self._token or details is None:
                return

            self.detail.show(**details)

        def failed(error):
            if token == self._token:
                self.detail.clear(str(error) or "Could not load details.")

        self.app.run(lambda: self.load_details(row), done, failed)


# --------------------------------------------------
# CRUD PANEL
# --------------------------------------------------

class EntityPanel(ListDetail):
    """
    A list/detail panel with Add / Edit / Delete for one table.

    The keys of the form fields must be the table's column names.
    """

    singular = "record"
    table_name = ""
    id_column = ""
    dependents = "other records"
    list_sql = ""
    form_columns = 1

    def buttons(self):
        return [
            (f"+  Add {self.singular}", self.add, "Accent.TButton", False),
            ("Edit", self.edit, "TButton", True),
            ("Delete", self.delete, "Danger.TButton", True),
        ]

    def activate(self, _row):
        self.edit()

    # ---------- hooks ----------

    def format_row(self, row):
        return tuple(row)

    def form_fields(self, current, context):
        raise NotImplementedError

    def load_context(self, cursor):
        """Extra data the form needs (drop-down choices)."""

        return {}

    def prepare(self, cursor, values):
        """Last chance to change the values before they are saved."""

        return values

    def describe(self, row):
        return f"{self.singular} {row[0]}"

    # ---------- list ----------

    def fetch_rows(self):
        with db_session() as cursor:
            cursor.execute(self.list_sql)
            return [self.format_row(row) for row in cursor.fetchall()]

    # ---------- add / edit ----------

    def add(self):
        def work():
            with db_session() as cursor:
                return self.load_context(cursor)

        self.app.run(work, lambda context: self._open_form(None, context))

    def edit(self):
        record_id = self.selected_id()

        if record_id is None:
            return

        columns = [f["key"] for f in self.form_fields(None, {})]

        def work():
            with db_session() as cursor:
                context = self.load_context(cursor)

                cursor.execute(
                    f"SELECT {', '.join(columns)} FROM {self.table_name} "
                    f"WHERE {self.id_column} = :record_id",
                    {"record_id": record_id}
                )
                row = cursor.fetchone()

            if row is None:
                raise UserError(
                    f"{self.singular.capitalize()} {record_id} not found."
                )

            return context, dict(zip(columns, row))

        self.app.run(
            work,
            lambda result: self._open_form(result[1], result[0], record_id)
        )

    def _open_form(self, current, context, record_id=None):
        editing = current is not None

        dialog = FormDialog(
            self, f"{'Edit' if editing else 'Add'} {self.singular}",
            self.form_fields(current, context),
            submit="Save changes" if editing else f"Add {self.singular}",
            columns=self.form_columns
        )
        values = dialog.show()

        if values is None:
            return

        if editing:
            self.app.run(
                lambda: self._update(record_id, values),
                lambda _r: self._saved(record_id, "updated")
            )
        else:
            self.app.run(
                lambda: self._insert(values),
                lambda new_id: self._saved(new_id, "added")
            )

    def _insert(self, values):
        with db_session() as cursor:
            values = self.prepare(cursor, dict(values))
            columns = list(values)
            new_id = cursor.var(int)

            cursor.execute(
                f"INSERT INTO {self.table_name} ({', '.join(columns)}) "
                f"VALUES ({', '.join(':' + c for c in columns)}) "
                f"RETURNING {self.id_column} INTO :new_id",
                {**values, "new_id": new_id}
            )

            return new_id.getvalue()[0]

    def _update(self, record_id, values):
        with db_session() as cursor:
            values = self.prepare(cursor, dict(values))
            assignments = ", ".join(f"{c} = :{c}" for c in values)

            cursor.execute(
                f"UPDATE {self.table_name} SET {assignments} "
                f"WHERE {self.id_column} = :record_id",
                {**values, "record_id": record_id}
            )

            if cursor.rowcount == 0:
                raise UserError(
                    f"{self.singular.capitalize()} {record_id} not found."
                )

    def _saved(self, record_id, verb):
        self.app.toast(f"{self.singular.capitalize()} {verb}.")
        self.refresh(select_key=(record_id,))

    # ---------- delete ----------

    def delete(self):
        row = self.table.selected()

        if row is None:
            return

        record_id = int(row[0])

        if not messagebox.askyesno(
                "Delete", f"Delete {self.describe(row)}?\n\n"
                          "This cannot be undone.",
                icon="warning", parent=self.winfo_toplevel()):
            return

        def work():
            with db_session() as cursor:
                try:
                    cursor.execute(
                        f"DELETE FROM {self.table_name} "
                        f"WHERE {self.id_column} = :record_id",
                        {"record_id": record_id}
                    )
                except oracledb.Error as error:
                    if "ORA-02292" in str(error):
                        raise UserError(
                            f"Cannot delete {self.singular} {record_id}: it "
                            f"is still used by {self.dependents}."
                        )

                    raise

                if cursor.rowcount == 0:
                    raise UserError(
                        f"{self.singular.capitalize()} {record_id} not found."
                    )

        self.app.run(work, lambda _r: self._deleted(record_id))

    def _deleted(self, record_id):
        self.app.toast(f"{self.singular.capitalize()} {record_id} deleted.")
        self.refresh()
