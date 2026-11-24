# gui_theme.py
# Colours, fonts and ttk styles shared by the whole graphical interface.

from tkinter import font as tkfont
from tkinter import ttk


# --------------------------------------------------
# PALETTE
# --------------------------------------------------

C = {
    "bg": "#f3f4f8",
    "surface": "#ffffff",
    "surface_alt": "#f9fafb",
    "hover": "#f3f4f6",
    "border": "#e5e7eb",
    "border_strong": "#d1d5db",
    "text": "#111827",
    "muted": "#6b7280",
    "faint": "#9ca3af",

    "sidebar": "#111827",
    "sidebar_hover": "#1f2937",
    "sidebar_text": "#d1d5db",
    "sidebar_muted": "#6b7280",

    "accent": "#4f46e5",
    "accent_hover": "#4338ca",
    "accent_soft": "#eef2ff",
    "select": "#e0e7ff",

    "danger": "#dc2626",
    "danger_soft": "#fef2f2",
    "success": "#059669",
    "success_soft": "#ecfdf5",
    "warning": "#d97706",
    "warning_soft": "#fffbeb",
}

FONT_FAMILY = "TkDefaultFont"
SCALE = 1.0


def px(value):
    """Scale a pixel size for high-DPI screens."""

    return int(round(value * SCALE))


def font(size=10, weight="normal"):
    """A font tuple in the family chosen for this machine."""

    return (FONT_FAMILY, size, weight)


def _pick_family(root):
    available = set(tkfont.families(root))

    for name in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu",
                 "Noto Sans", "DejaVu Sans"):
        if name in available:
            return name

    return tkfont.nametofont("TkDefaultFont").actual("family")


# --------------------------------------------------
# STYLES
# --------------------------------------------------

def apply_theme(root):
    """Configure ttk and Tk defaults. Call once, right after creating root."""

    global FONT_FAMILY, SCALE
    FONT_FAMILY = _pick_family(root)
    SCALE = max(1.0, root.winfo_fpixels("1i") / 96)

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(family=FONT_FAMILY, size=10)

    root.configure(bg=C["bg"])
    root.option_add("*TCombobox*Listbox.background", C["surface"])
    root.option_add("*TCombobox*Listbox.foreground", C["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", C["select"])
    root.option_add("*TCombobox*Listbox.selectForeground", C["text"])
    root.option_add("*TCombobox*Listbox.font", font(10))

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".", background=C["bg"], foreground=C["text"], font=font(10),
        bordercolor=C["border"], focuscolor=C["bg"], troughcolor=C["bg"],
    )

    _frames_and_labels(style)
    _buttons(style)
    _inputs(style)
    _tables(style)
    _scrollbars(style)
    _progress(style)


def _frames_and_labels(style):
    style.configure("TFrame", background=C["bg"])
    style.configure("Card.TFrame", background=C["surface"])
    style.configure("Alt.TFrame", background=C["surface_alt"])

    style.configure("TLabel", background=C["bg"], foreground=C["text"])
    style.configure("Card.TLabel", background=C["surface"])
    style.configure(
        "Title.TLabel", font=font(20, "bold"), foreground=C["text"]
    )
    style.configure("Subtitle.TLabel", foreground=C["muted"])
    style.configure(
        "CardTitle.TLabel", background=C["surface"], font=font(12, "bold")
    )
    style.configure(
        "CardMuted.TLabel", background=C["surface"], foreground=C["muted"]
    )
    style.configure(
        "Field.TLabel", background=C["surface"], foreground=C["muted"],
        font=font(9, "bold"),
    )
    style.configure(
        "Error.TLabel", background=C["surface"], foreground=C["danger"],
        font=font(9),
    )
    style.configure(
        "Hint.TLabel", background=C["surface"], foreground=C["faint"],
        font=font(9),
    )
    style.configure(
        "KPIValue.TLabel", background=C["surface"], font=font(22, "bold")
    )
    style.configure(
        "KPILabel.TLabel", background=C["surface"], foreground=C["muted"],
        font=font(9, "bold"),
    )
    style.configure(
        "Total.TLabel", background=C["surface"], font=font(14, "bold")
    )

    style.configure(
        "TCheckbutton", background=C["bg"], focuscolor=C["bg"]
    )
    style.configure(
        "Card.TCheckbutton", background=C["surface"],
        focuscolor=C["surface"],
    )
    style.map("Card.TCheckbutton", background=[("active", C["surface"])])


def _button(style, name, bg, fg, border, hover, disabled_fg=None):
    style.configure(
        name, background=bg, foreground=fg, bordercolor=border,
        lightcolor=bg, darkcolor=bg, focuscolor=bg, relief="solid",
        borderwidth=1, padding=(14, 7), font=font(10, "bold"),
    )
    style.map(
        name,
        background=[("disabled", C["hover"]), ("active", hover)],
        foreground=[("disabled", disabled_fg or C["faint"])],
        bordercolor=[("disabled", C["border"]), ("active", border)],
        lightcolor=[("disabled", C["hover"]), ("active", hover)],
        darkcolor=[("disabled", C["hover"]), ("active", hover)],
    )


def _buttons(style):
    _button(
        style, "TButton", C["surface"], C["text"], C["border_strong"],
        C["hover"],
    )
    _button(
        style, "Accent.TButton", C["accent"], "#ffffff", C["accent"],
        C["accent_hover"],
    )
    _button(
        style, "Danger.TButton", C["surface"], C["danger"], "#fecaca",
        C["danger_soft"],
    )
    _button(
        style, "Ghost.TButton", C["surface"], C["muted"], C["surface"],
        C["hover"],
    )


def _inputs(style):
    field = dict(
        fieldbackground=C["surface"], background=C["surface"],
        foreground=C["text"], bordercolor=C["border_strong"],
        lightcolor=C["border_strong"], darkcolor=C["border_strong"],
        padding=(8, 6), borderwidth=1, insertcolor=C["text"],
        selectbackground=C["select"], selectforeground=C["text"],
    )

    focus = [("focus", C["accent"])]

    style.configure("TEntry", **field)
    style.map(
        "TEntry", bordercolor=focus, lightcolor=focus, darkcolor=focus
    )

    style.configure("TCombobox", arrowcolor=C["muted"], **field)
    style.map(
        "TCombobox",
        bordercolor=focus, lightcolor=focus, darkcolor=focus,
        fieldbackground=[("readonly", C["surface"]),
                         ("disabled", C["hover"])],
        foreground=[("disabled", C["faint"])],
        selectbackground=[("readonly", C["surface"])],
        selectforeground=[("readonly", C["text"])],
        arrowcolor=[("disabled", C["faint"])],
    )

    style.configure(
        "TSpinbox", arrowcolor=C["muted"], **field
    )
    style.map(
        "TSpinbox", bordercolor=focus, lightcolor=focus, darkcolor=focus
    )


def _tables(style):
    style.configure(
        "Treeview", background=C["surface"], fieldbackground=C["surface"],
        foreground=C["text"], rowheight=px(32), borderwidth=0, font=font(10),
    )
    style.map(
        "Treeview",
        background=[("selected", C["select"])],
        foreground=[("selected", C["text"])],
    )
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

    style.configure(
        "Treeview.Heading", background=C["surface_alt"],
        foreground=C["muted"], font=font(9, "bold"), relief="flat",
        padding=(10, 9), borderwidth=0, lightcolor=C["surface_alt"],
        darkcolor=C["surface_alt"], bordercolor=C["border"],
    )
    style.map("Treeview.Heading", background=[("active", C["hover"])])

    style.configure("Compact.Treeview", rowheight=px(27), font=font(9))
    style.configure(
        "Compact.Treeview.Heading", padding=(8, 6), font=font(8, "bold")
    )
    style.layout("Compact.Treeview", [("Treeview.treearea",
                                       {"sticky": "nswe"})])


def _scrollbars(style):
    for orient, side in (("Vertical", "ns"), ("Horizontal", "we")):
        name = f"{orient}.TScrollbar"

        style.configure(
            name, background=C["border_strong"], troughcolor=C["surface"],
            bordercolor=C["surface"], lightcolor=C["border_strong"],
            darkcolor=C["border_strong"], relief="flat", gripcount=0,
            arrowsize=0, width=px(10),
        )
        style.map(name, background=[("active", C["faint"])])
        style.layout(name, [(
            f"{orient}.Scrollbar.trough",
            {"sticky": side, "children": [(
                f"{orient}.Scrollbar.thumb",
                {"expand": "1", "sticky": "nswe"},
            )]},
        )])


def _progress(style):
    style.configure(
        "Thin.Horizontal.TProgressbar", background=C["accent"],
        troughcolor=C["bg"], bordercolor=C["bg"], lightcolor=C["accent"],
        darkcolor=C["accent"], thickness=3,
    )
