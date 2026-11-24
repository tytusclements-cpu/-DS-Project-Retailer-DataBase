# gui_widgets.py
# Reusable building blocks for the graphical interface: cards, sortable and
# filterable tables, searchable drop-downs, tabs and a details panel.

import tkinter as tk
from tkinter import ttk

from gui_theme import C, font, px


# --------------------------------------------------
# CARD
# --------------------------------------------------

class Card(tk.Frame):
    """A white panel with a thin border."""

    def __init__(self, parent, **options):
        super().__init__(
            parent, bg=C["surface"], highlightbackground=C["border"],
            highlightcolor=C["border"], highlightthickness=1, **options
        )


# --------------------------------------------------
# SEARCH BOX
# --------------------------------------------------

class SearchBox(ttk.Frame):
    """Label + entry that reports every change; Escape clears it."""

    def __init__(self, parent, command, label="Search", width=24):
        super().__init__(parent, style="Card.TFrame")

        self._command = command
        self.var = tk.StringVar()

        ttk.Label(self, text=label, style="CardMuted.TLabel").pack(
            side="left", padx=(0, 8)
        )

        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(side="left")
        self.entry.bind("<Escape>", lambda _e: self.var.set(""))

        self.var.trace_add("write", lambda *_: self._command(self.var.get()))

    def focus(self):
        self.entry.focus_set()
        self.entry.select_range(0, "end")


# --------------------------------------------------
# DATA TABLE
# --------------------------------------------------

def _sort_key(value):
    """Sort numbers (also "$1,234.50") numerically and text alphabetically."""

    text = "" if value is None else str(value)
    number = text.replace("$", "").replace(",", "").strip()

    try:
        return (0, float(number), "")
    except ValueError:
        return (1, 0.0, text.lower())


class DataTable(tk.Frame):
    """
    A read-only table.

    columns: list of (heading, width, anchor, stretch) - the last two are
             optional ("w" and False by default).
    Click a heading to sort, call set_filter() to narrow rows by text.
    on_select(values_or_None) fires when the selection changes;
    on_activate(values) on double-click or Enter.
    """

    ROW_TAGS = {
        "low": {"background": C["warning_soft"]},
        "out": {"background": C["danger_soft"], "foreground": C["danger"]},
    }

    def __init__(self, parent, columns, on_select=None, on_activate=None,
                 compact=False, footer=True, height=None, key_columns=(0,),
                 empty_text="No records found"):
        super().__init__(parent, bg=C["surface"])

        self._columns = [self._normalise(c) for c in columns]
        self._base_widths = [c[1] for c in self._columns]
        self._shrunk = False
        self._on_select = on_select
        self._on_activate = on_activate
        self._key_columns = key_columns
        self._empty_text = empty_text
        self._rows = []              # (values, tag)
        self._filter = ""
        self._sort = None            # (column index, reverse)
        self._quiet = False
        self._extra = ""

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        options = {"height": height} if height else {}
        self.tree = ttk.Treeview(
            self, columns=[f"c{i}" for i in range(len(self._columns))],
            show="headings", selectmode="browse",
            style="Compact.Treeview" if compact else "Treeview", **options
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        self._vsb = ttk.Scrollbar(
            self, orient="vertical", command=self.tree.yview
        )
        self._vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=self._on_yscroll)

        self.tree.tag_configure("odd", background=C["surface_alt"])
        self.tree.tag_configure("even", background=C["surface"])

        for name, options in self.ROW_TAGS.items():
            self.tree.tag_configure(name, **options)

        for index, (heading, width, anchor, stretch) in enumerate(
                self._columns):
            self.tree.heading(
                f"c{index}", text=heading, anchor=anchor,
                command=lambda i=index: self._sort_by(i)
            )
            self.tree.column(
                f"c{index}", width=width, minwidth=40, anchor=anchor,
                stretch=stretch
            )

        self._empty = tk.Label(
            self.tree, text=empty_text, bg=C["surface"], fg=C["faint"],
            font=font(10)
        )

        self._footer = None

        if footer:
            self._footer = tk.Label(
                self, anchor="w", bg=C["surface_alt"], fg=C["muted"],
                font=font(9), padx=12, pady=6
            )
            self._footer.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.tree.bind("<Configure>", self._fit_columns)
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", self._double_click)
        self.tree.bind("<Return>", lambda _e: self._activate())

    @staticmethod
    def _normalise(column):
        heading, width, *rest = column
        anchor = rest[0] if len(rest) > 0 else "w"
        stretch = rest[1] if len(rest) > 1 else False
        return heading, px(width), anchor, stretch

    # ---------- data ----------

    def set_rows(self, rows, tags=None):
        """Replace all rows. Keeps the selected record selected if it exists."""

        previous = self._selected_key()

        self._rows = [
            (tuple(row), tags[i] if tags else None)
            for i, row in enumerate(rows)
        ]
        self._render(previous_key=previous, force_notify=True)

    def set_filter(self, text):
        previous = self._selected_key()
        self._filter = text.strip().lower()
        self._render(previous_key=previous)

    def set_extra(self, text):
        """Extra text shown in the footer after the record count."""

        self._extra = text
        self._update_footer(self._visible_count())

    def all_rows(self):
        return [values for values, _ in self._rows]

    def visible_rows(self):
        return [self._rows[int(i)][0] for i in self.tree.get_children()]

    def headings(self):
        return [heading for heading, *_ in self._columns]

    def selected(self):
        selection = self.tree.selection()

        if not selection:
            return None

        return self._rows[int(selection[0])][0]

    def select_key(self, key):
        """Select the visible row whose key columns equal `key`."""

        for iid in self.tree.get_children():
            if self._key_of(self._rows[int(iid)][0]) == tuple(key):
                self.tree.selection_set(iid)
                self.tree.see(iid)
                return True

        return False

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    # ---------- rendering ----------

    def _key_of(self, values):
        return tuple(values[k] for k in self._key_columns)

    def _selected_key(self):
        values = self.selected()
        return None if values is None else self._key_of(values)

    def _matches(self, values):
        if not self._filter:
            return True

        return any(
            self._filter in ("" if v is None else str(v)).lower()
            for v in values
        )

    def _render(self, previous_key=None, force_notify=False):
        self._quiet = True

        try:
            self.tree.delete(*self.tree.get_children())

            indexes = [
                i for i, (values, _) in enumerate(self._rows)
                if self._matches(values)
            ]

            if self._sort is not None:
                column, reverse = self._sort
                indexes.sort(
                    key=lambda i: _sort_key(self._rows[i][0][column]),
                    reverse=reverse
                )

            for position, i in enumerate(indexes):
                values, tag = self._rows[i]
                self.tree.insert(
                    "", "end", iid=str(i),
                    values=["" if v is None else v for v in values],
                    tags=(tag or ("odd" if position % 2 else "even"),)
                )

            restored = None

            if previous_key is not None:
                for i in indexes:
                    if self._key_of(self._rows[i][0]) == previous_key:
                        restored = i
                        break

            if restored is not None:
                self.tree.selection_set(str(restored))
                self.tree.see(str(restored))

        finally:
            self._quiet = False

        self._update_empty(len(indexes))
        self._update_footer(len(indexes))
        self._refresh_headings()

        if force_notify or self._selected_key() != previous_key:
            self._notify()

    def _visible_count(self):
        return len(self.tree.get_children())

    def _update_empty(self, visible):
        if visible:
            self._empty.place_forget()
            return

        self._empty.configure(
            text="No rows match your search." if self._rows
            else self._empty_text
        )
        self._empty.place(relx=0.5, rely=0.42, anchor="center")

    def _update_footer(self, visible):
        if self._footer is None:
            return

        total = len(self._rows)
        noun = "record" if total == 1 else "records"

        if visible == total:
            text = f"{total} {noun}"
        else:
            text = f"{visible} of {total} {noun}"

        if self._extra:
            text += f"   ·   {self._extra}"

        self._footer.configure(text=text)

    def _on_yscroll(self, first, last):
        self._vsb.set(first, last)

        if float(first) <= 0.0 and float(last) >= 1.0:
            self._vsb.grid_remove()
        else:
            self._vsb.grid()

    # ---------- layout ----------

    MIN_COLUMN = 56

    def _fit_columns(self, _event=None):
        """Shrink columns proportionally when the table is too narrow."""

        available = self.tree.winfo_width() - 2

        if available <= 1:
            return

        base = self._base_widths
        total = sum(base)

        if total <= available:
            if self._shrunk:
                for index, width in enumerate(base):
                    self.tree.column(f"c{index}", width=width)

                self._shrunk = False

            return

        minimum = px(self.MIN_COLUMN)
        slack = [max(width - minimum, 0) for width in base]

        if not sum(slack):
            return

        cut = min((total - available) / sum(slack), 1.0)

        for index, (width, spare) in enumerate(zip(base, slack)):
            self.tree.column(f"c{index}", width=int(width - spare * cut))

        self._shrunk = True

    # ---------- sorting ----------

    def _sort_by(self, column):
        previous = self._selected_key()

        if self._sort and self._sort[0] == column:
            self._sort = (column, not self._sort[1])
        else:
            self._sort = (column, False)

        self._render(previous_key=previous)

    def _refresh_headings(self):
        for index, (heading, *_rest) in enumerate(self._columns):
            arrow = ""

            if self._sort and self._sort[0] == index:
                arrow = "  ▼" if self._sort[1] else "  ▲"

            self.tree.heading(f"c{index}", text=heading + arrow)

    # ---------- events ----------

    def _notify(self):
        if self._on_select is not None:
            self._on_select(self.selected())

    def _selection_changed(self, _event):
        if not self._quiet:
            self._notify()

    def _double_click(self, event):
        if self.tree.identify_row(event.y):
            self._activate()

    def _activate(self):
        values = self.selected()

        if values is not None and self._on_activate is not None:
            self._on_activate(values)


# --------------------------------------------------
# CHOICE BOX
# --------------------------------------------------

class ChoiceBox(ttk.Combobox):
    """
    A drop-down of (id, label) pairs you can also type into to narrow the
    list. value() returns the chosen id, None for "nothing chosen", or - when
    editable - the typed text if it matches no label.
    """

    _NAVIGATION = {
        "Up", "Down", "Left", "Right", "Return", "Tab", "Escape", "Shift_L",
        "Shift_R", "Control_L", "Control_R", "Home", "End", "Prior", "Next",
    }

    def __init__(self, parent, choices=(), editable=False, blank=None,
                 width=32, **options):
        super().__init__(parent, width=width, **options)

        self.editable = editable
        self.blank = blank
        self._choices = []
        self._labels = []

        self.set_choices(choices)
        self.bind("<KeyRelease>", self._narrow)

        if blank:
            self.set(blank)

    def set_choices(self, choices):
        self._choices = list(choices)
        self._labels = [label for _, label in self._choices]

        if self.blank:
            self._labels.insert(0, self.blank)

        self.configure(values=self._labels)

    def reset_filter(self):
        self.configure(values=self._labels)

    def _narrow(self, event):
        if event.keysym in self._NAVIGATION:
            return

        text = self.get().strip().lower()

        if not text:
            self.configure(values=self._labels)
            return

        self.configure(
            values=[label for label in self._labels if text in label.lower()]
        )

    def value(self):
        text = self.get().strip()

        if not text or (self.blank and text == self.blank):
            return None

        for choice_id, label in self._choices:
            if label.lower() == text.lower():
                return choice_id

        if self.editable:
            return text

        raise ValueError("Choose an option from the list.")

    def set_value(self, choice_id):
        for known_id, label in self._choices:
            if known_id == choice_id:
                self.set(label)
                return

        if self.editable and isinstance(choice_id, str):
            self.set(choice_id)
        else:
            self.set(self.blank or "")


# --------------------------------------------------
# TABS
# --------------------------------------------------

class Tabs(tk.Frame):
    """A row of text tabs with an accent underline on the active one."""

    def __init__(self, parent, tabs, on_change):
        super().__init__(parent, bg=C["bg"])

        self._on_change = on_change
        self._labels = []
        self._bars = []
        self.current = 0

        for index, text in enumerate(tabs):
            cell = tk.Frame(self, bg=C["bg"])
            cell.pack(side="left", padx=(0, 22))

            label = tk.Label(
                cell, text=text, bg=C["bg"], fg=C["muted"],
                font=font(11, "bold"), cursor="hand2", pady=6
            )
            label.pack()

            bar = tk.Frame(cell, bg=C["bg"], height=3)
            bar.pack(fill="x")

            label.bind("<Button-1>", lambda _e, i=index: self.select(i))
            self._labels.append(label)
            self._bars.append(bar)

        self.select(0, notify=False)

    def select(self, index, notify=True):
        self.current = index

        for i, (label, bar) in enumerate(zip(self._labels, self._bars)):
            active = i == index
            label.configure(fg=C["accent"] if active else C["muted"])
            bar.configure(bg=C["accent"] if active else C["bg"])

        if notify:
            self._on_change(index)


# --------------------------------------------------
# SCROLLABLE FRAME
# --------------------------------------------------

class ScrollFrame(tk.Frame):
    """A vertically scrollable area; put widgets in `.inner`."""

    def __init__(self, parent):
        super().__init__(parent, bg=C["surface"])

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            self, bg=C["surface"], highlightthickness=0, borderwidth=0
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._bar = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._bar.grid(row=0, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=self._bar.set)

        self.inner = ttk.Frame(self._canvas, style="Card.TFrame")
        self._window = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )

        self.inner.bind("<Configure>", self._inner_resized)
        self._canvas.bind("<Configure>", self._canvas_resized)
        self._canvas.bind("<Enter>", self._bind_wheel)
        self._canvas.bind("<Leave>", self._unbind_wheel)
        self.inner.bind("<Enter>", self._bind_wheel)

    def scroll_to_top(self):
        self._canvas.yview_moveto(0)

    def _inner_resized(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        needed = self.inner.winfo_reqheight()
        available = self._canvas.winfo_height()

        if needed <= available:
            self._bar.grid_remove()
        else:
            self._bar.grid()

    def _canvas_resized(self, event):
        self._canvas.itemconfigure(self._window, width=event.width)
        self._inner_resized(None)

    def _bind_wheel(self, _event):
        self._canvas.bind_all("<MouseWheel>", self._wheel)

    def _unbind_wheel(self, event):
        # Moving onto a child still counts as inside.
        x, y = self.winfo_pointerxy()

        if self.winfo_containing(x, y) is not None and str(
                self.winfo_containing(x, y)).startswith(str(self)):
            return

        self._canvas.unbind_all("<MouseWheel>")

    def _wheel(self, event):
        try:
            if event.widget.winfo_class() == "Treeview":
                return
        except (AttributeError, tk.TclError):
            pass

        if self.inner.winfo_reqheight() > self._canvas.winfo_height():
            self._canvas.yview_scroll(int(-event.delta / 120), "units")


# --------------------------------------------------
# DETAILS PANEL
# --------------------------------------------------

class DetailPanel(Card):
    """
    The panel beside a list. show() renders a title, label/value pairs and
    any number of small tables; clear() returns it to the empty state.
    """

    def __init__(self, parent, width=360,
                 empty="Select a row to see its details."):
        super().__init__(parent, width=px(width))

        self._empty = empty
        self.grid_propagate(False)
        self.pack_propagate(False)

        self._scroll = ScrollFrame(self)
        self._scroll.pack(fill="both", expand=True)
        self.body = self._scroll.inner

        self.clear()

    def _reset(self):
        for child in self.body.winfo_children():
            child.destroy()

        self._scroll.scroll_to_top()

    def clear(self, message=None):
        self._reset()

        ttk.Label(
            self.body, text=message or self._empty,
            style="CardMuted.TLabel", wraplength=px(280), justify="center"
        ).pack(pady=60, padx=20)

    def loading(self):
        self.clear("Loading…")

    def show(self, title, subtitle=None, fields=(), tables=()):
        """
        fields: [(label, value)]
        tables: [(heading, columns, rows)] - columns as for DataTable.
        """

        self._reset()

        pad = ttk.Frame(self.body, style="Card.TFrame", padding=(18, 16))
        pad.pack(fill="both", expand=True)

        ttk.Label(
            pad, text=title, style="CardTitle.TLabel", wraplength=px(300),
            justify="left"
        ).pack(anchor="w")

        if subtitle:
            ttk.Label(
                pad, text=subtitle, style="CardMuted.TLabel", wraplength=px(300),
                justify="left"
            ).pack(anchor="w", pady=(2, 0))

        if fields:
            grid = ttk.Frame(pad, style="Card.TFrame")
            grid.pack(fill="x", pady=(14, 0))
            grid.columnconfigure(1, weight=1)

            for row, (label, value) in enumerate(fields):
                ttk.Label(
                    grid, text=label, style="CardMuted.TLabel"
                ).grid(row=row, column=0, sticky="nw", pady=3,
                       padx=(0, 14))

                ttk.Label(
                    grid, text="—" if value in (None, "") else str(value),
                    style="Card.TLabel", wraplength=px(190), justify="left"
                ).grid(row=row, column=1, sticky="nw", pady=3)

        for heading, columns, rows in tables:
            ttk.Label(
                pad, text=heading.upper(), style="Field.TLabel"
            ).pack(anchor="w", pady=(20, 6))

            if not rows:
                ttk.Label(
                    pad, text="Nothing yet.", style="Hint.TLabel"
                ).pack(anchor="w")
                continue

            table = DataTable(
                pad, columns, compact=True, footer=False,
                height=max(1, min(len(rows), 6))
            )
            table.pack(fill="x")
            table.set_rows(rows)
