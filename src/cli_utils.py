# cli_utils.py
# Shared helpers for the console application: validated input, table output,
# friendly database error messages, and a reusable menu loop.

import re
from decimal import Decimal, InvalidOperation

import oracledb

from database import DatabaseUnavailableError, db_session


# --------------------------------------------------
# EXCEPTIONS
# --------------------------------------------------

class Cancelled(Exception):
    """The user typed 'cancel' (or input ended) while answering a prompt."""


class UserError(Exception):
    """
    A problem the user should be told about (record not found, not enough
    stock, ...). Raising it inside a db_session() block rolls the
    transaction back.
    """


# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[0-9+()\-.\s]{7,30}$")
POSTAL_PATTERN = re.compile(r"^[A-Za-z0-9\- ]{3,20}$")


def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(value))


def is_valid_phone(value):
    return bool(PHONE_PATTERN.match(value))


def is_valid_postal_code(value):
    return bool(POSTAL_PATTERN.match(value))


# --------------------------------------------------
# PROMPTS
# --------------------------------------------------
# Every prompt accepts the word "cancel" to abandon the current action.
# If input ends (Ctrl+Z / Ctrl+D / piped input runs out) the action is
# cancelled rather than crashing.

def ask(label):
    """Read one trimmed line of input."""

    try:
        value = input(label).strip()
    except EOFError:
        raise Cancelled()

    if value.lower() == "cancel":
        raise Cancelled()

    return value


def prompt_text(label, required=True, max_len=None, default=None,
                validator=None, error="Invalid value."):
    """
    Ask for text.

    default: when given (update screens), a blank answer keeps the current
             value and "-" clears an optional field.
    Returns the text, or None for an empty optional answer.
    """

    suffix = ""
    if default is not None:
        suffix = f" [{default}]"
    elif not required:
        suffix = " (optional)"

    while True:
        value = ask(f"{label}{suffix}: ")

        if value == "":
            if default is not None:
                return default
            if not required:
                return None
            print("This field is required.")
            continue

        if value == "-" and default is not None and not required:
            return None

        if max_len is not None and len(value) > max_len:
            print(f"Please enter at most {max_len} characters.")
            continue

        if validator is not None and not validator(value):
            print(error)
            continue

        return value


def prompt_int(label, minimum=None, maximum=None, required=True,
               default=None):
    """Ask for a whole number within optional bounds."""

    suffix = f" [{default}]" if default is not None else ""

    while True:
        value = ask(f"{label}{suffix}: ")

        if value == "":
            if default is not None:
                return default
            if not required:
                return None
            print("This field is required.")
            continue

        try:
            number = int(value)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if minimum is not None and number < minimum:
            print(f"Value must be at least {minimum}.")
            continue

        if maximum is not None and number > maximum:
            print(f"Value must be at most {maximum}.")
            continue

        return number


def prompt_money(label, default=None):
    """Ask for a non-negative dollar amount with at most two decimals."""

    suffix = f" [{default}]" if default is not None else ""

    while True:
        value = ask(f"{label}{suffix}: ")

        if value == "" and default is not None:
            return Decimal(str(default))

        try:
            amount = Decimal(value.replace("$", "").replace(",", ""))
        except InvalidOperation:
            print("Please enter a valid amount, for example 3.99.")
            continue

        if not amount.is_finite():
            print("Please enter a valid amount, for example 3.99.")
            continue

        if amount < 0:
            print("Amount cannot be negative.")
            continue

        if amount != amount.quantize(Decimal("0.01")):
            print("Use at most two decimal places.")
            continue

        if amount > Decimal("99999999.99"):
            print("Amount is too large.")
            continue

        return amount


def confirm(question):
    """Ask a yes/no question; anything but y/yes means no."""

    return ask(f"{question} (y/n): ").lower() in ("y", "yes")


# --------------------------------------------------
# OUTPUT
# --------------------------------------------------

def money(value):
    """Format a number as dollars."""

    return f"${float(value or 0):,.2f}"


def fmt_dt(value):
    """Format a timestamp as YYYY-MM-DD HH:MM (blank if missing)."""

    return "" if value is None else value.strftime("%Y-%m-%d %H:%M")


def print_table(headers, rows):
    """Print rows as an aligned text table."""

    text_rows = [
        ["" if cell is None else str(cell) for cell in row]
        for row in rows
    ]

    widths = [len(header) for header in headers]

    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(cells):
        return " | ".join(
            cell.ljust(widths[index]) for index, cell in enumerate(cells)
        ).rstrip()

    print(line(headers))
    print("-+-".join("-" * width for width in widths))

    for row in text_rows:
        print(line(row))

    print(f"({len(text_rows)} row{'s' if len(text_rows) != 1 else ''})")


def print_record(fields):
    """Print (label, value) pairs one per line."""

    width = max(len(label) for label, _ in fields)

    for label, value in fields:
        print(f"  {label.ljust(width)} : {'' if value is None else value}")


def like_pattern(term):
    """
    Build a LIKE pattern that matches the term literally.
    Use together with: LIKE :search ESCAPE '\\'
    """

    escaped = (
        term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )

    return f"%{escaped}%"


# --------------------------------------------------
# DATABASE ERRORS
# --------------------------------------------------

CONSTRAINT_MESSAGES = {
    "UQ_CUSTOMERS_EMAIL": "A customer with that email already exists.",
    "UQ_STORES_LOCATION_NAME":
        "A store with that name already exists in that city and state.",
    "UQ_VENDORS_LOCATION_NAME":
        "A vendor with that name already exists in that city and state.",
    "UQ_BRANDS_NAME": "A brand with that name already exists.",
    "UQ_PRODUCT_TYPES_NAME": "A product type with that name already exists.",
    "PK_INVENTORY": "That product is already stocked at that store.",
    "PK_SALE_ITEMS": "That product is already part of this sale.",
    "PK_WEB_ORDER_ITEMS": "That product is already part of this order.",
    "PK_REORDER_ITEMS": "That product is already part of this reorder.",
    "CK_INVENTORY_QUANTITY": "Inventory quantity cannot be negative.",
    "CK_PRODUCTS_PRICE": "Price cannot be negative.",
}


def describe_db_error(error):
    """Turn an Oracle error into a short message a user can act on."""

    text = str(error)

    constraint = re.search(r"\(([A-Z0-9_$#]+\.)?([A-Z0-9_$#]+)\)", text)
    name = constraint.group(2) if constraint else None

    if name in CONSTRAINT_MESSAGES:
        return CONSTRAINT_MESSAGES[name]

    if "ORA-00001" in text:
        return "That record already exists."

    if "ORA-02291" in text:
        return "A referenced record (store, product, customer, ...) does not exist."

    if "ORA-02292" in text:
        return "Cannot delete: other records still depend on this one."

    if "ORA-02290" in text:
        return "A value violates a data rule (for example a negative number)."

    if "ORA-01400" in text:
        return "A required value is missing."

    if "ORA-12899" in text:
        return "A value is too long for its field."

    return text.strip().splitlines()[0] if text.strip() else "Unknown database error."


# --------------------------------------------------
# LOOKUPS
# --------------------------------------------------

def require_row(cursor, sql, params, message):
    """Run a query that must return a row; raise UserError(message) if not."""

    cursor.execute(sql, params)
    row = cursor.fetchone()

    if row is None:
        raise UserError(message)

    return row


# --------------------------------------------------
# GENERIC DELETE
# --------------------------------------------------

def delete_by_id(table, id_column, record_id, label, dependents):
    """
    Delete one row by its ID after confirmation.

    table / id_column are fixed names supplied by the calling module (never
    user input). dependents is a phrase such as "inventory, sales or orders"
    used in the message when foreign keys block the delete.
    """

    if not confirm(f"Delete {label} {record_id}? This cannot be undone"):
        print("Delete cancelled.")
        return

    with db_session() as cursor:
        try:
            cursor.execute(
                f"DELETE FROM {table} WHERE {id_column} = :record_id",
                {"record_id": record_id}
            )
        except oracledb.Error as error:
            if "ORA-02292" in str(error):
                raise UserError(
                    f"Cannot delete {label} {record_id}: it is still used by "
                    f"{dependents}."
                )
            raise

        if cursor.rowcount == 0:
            raise UserError(f"{label.capitalize()} {record_id} not found.")

    print(f"{label.capitalize()} {record_id} deleted.")


# --------------------------------------------------
# ACTION AND MENU HELPERS
# --------------------------------------------------

def run_action(action):
    """
    Run one menu action and report any problem instead of crashing.
    Returns True if the action finished without error.
    """

    try:
        action()
        return True

    except Cancelled:
        print("\nCancelled.")

    except UserError as error:
        print(f"\n{error}")

    except DatabaseUnavailableError as error:
        print(f"\n{error}")

    except oracledb.Error as error:
        print(f"\nDatabase error: {describe_db_error(error)}")

    return False


def run_menu(title, items):
    """
    Show a numbered menu until the user returns.

    items: list of (label, function) pairs. A final
           "Return to Main Menu" option is added automatically.
    """

    back = str(len(items) + 1)

    while True:
        print(f"\n===== {title} =====")

        for number, (label, _) in enumerate(items, start=1):
            print(f"{number}. {label}")

        print(f"{back}. Return to Main Menu")

        try:
            choice = input("Select an option: ").strip()
        except EOFError:
            return

        if choice == back:
            return

        if choice.isdigit() and 1 <= int(choice) <= len(items):
            run_action(items[int(choice) - 1][1])
        else:
            print(f"Invalid option. Please enter a number from 1 to {back}.")
