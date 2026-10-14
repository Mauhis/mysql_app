"""Interactive command-line workflow for the MySQL database application."""

from getpass import getpass

import mysql.connector

from ConnManager import ConnectionManager
from database_operations import DatabaseOperations
from table_operations import TableOperations
from validation import validate_identifier
from column_values import ColumnValues


MENU = (
    "\nMain menu\n1. Database actions\n2. Table actions\n0. Exit"
)
DATABASE_MENU = (
    "\nDatabase actions\n1. List databases\n2. Create database\n"
    "3. Modify database defaults\n4. Delete database\n0. Return to main menu"
)
TABLE_MENU = (
    "\nTable actions\n5. Create table\n"
    "6. List tables\n7. View table contents\n8. Add typed rows\n9. Modify table columns\n"
    "10. Edit existing row values\n0. Return to main menu"
)


def read_port():
    """Prompt for a valid TCP port, using 3306 when the input is blank."""
    while True:
        value = input("Port [3306]: ").strip() or "3306"
        if value.isascii() and value.isdecimal() and 1 <= int(value) <= 65535:
            return int(value)
        print("Enter a port between 1 and 65535.")


def connect_to_server(db):
    """Prompt for connection settings and open the server connection."""
    host = input("Host [localhost]: ").strip() or "localhost"
    port = read_port()
    user = input("Username [root]: ").strip() or "root"
    password = getpass("Password: ")
    db.connect(host, user, password, port)


def read_existing_database(db, *, protect_system=True):
    """Return a validated, visible database selected by the user."""
    name = input("Existing database name: ").strip()
    validate_identifier(name, protect_system=protect_system)
    if name not in db.list_databases():
        raise ValueError("Choose an exact database name from the database list.")
    return name


def list_databases(db):
    """Print the databases visible to the current account."""
    names = db.list_databases()
    print("\n".join(names) if names else "No databases visible.")


def create_database(db):
    """Prompt for and create a database."""
    name = input("New database name: ").strip()
    db.create_database(name)
    print(f"Database '{name}' created successfully.")


def list_tables(db, tables):
    """Print visible tables and views in the selected database."""
    database = read_existing_database(db, protect_system=False)
    names = tables.list_tables(database)
    print("\n".join(names) if names else "No tables visible.")


def view_table(db, tables):
    """Display a selected table's column names and values."""
    database = read_existing_database(db, protect_system=False)
    names = tables.list_tables(database)
    if not names:
        print("No tables visible.")
        return
    print("Tables:\n" + "\n".join(names))
    name = input("Table name: ").strip()
    if name not in names:
        raise ValueError("Choose an exact table name from the table list.")
    columns, rows = tables.read_table(database, name)
    # repr keeps newlines/tabs on one line and distinguishes text from SQL NULL.
    rendered = [["NULL" if value is None else repr(value)
                 if isinstance(value, (str, bytes)) else str(value)
                 for value in row] for row in rows]
    widths = [max(len(column), *(len(row[i]) for row in rendered), 1)
              for i, column in enumerate(columns)]

    def print_row(values):
        print(" | ".join(value.ljust(width) for value, width in zip(values, widths)))

    print_row(columns)
    print("-+-".join("-" * width for width in widths))
    for row in rendered:
        print_row(row)
    print(f"{len(rows)} row(s)." if rows else "Table is empty.")


def create_table(db, tables):
    """Collect columns and create a table in an existing database."""
    database = read_existing_database(db)
    name = input("New table name: ").strip()
    columns = {}
    print(
        "Types: INT, BIGINT, FLOAT, DOUBLE, BOOLEAN, DATE, DATETIME, "
        "TIMESTAMP, TEXT, VARCHAR(n), DECIMAL(p, s)."
    )
    while True:
        column = input("Column name (blank to finish): ").strip()
        if not column:
            break
        if column.lower() in {existing.lower() for existing in columns}:
            raise ValueError("Column names must be unique regardless of case.")
        columns[column] = input("Column type: ").strip()
    primary_key = input("Primary key column (blank for none): ").strip() or None
    tables.create_table(database, name, columns, primary_key=primary_key)
    print(f"Table '{database}.{name}' created successfully.")


def modify_table(db, tables):
    """Add or remove columns on a selected existing table."""
    database = read_existing_database(db)
    names = tables.list_tables(database)
    if not names:
        print("No tables visible. Create a table first with option 5.")
        return
    print("Tables:\n" + "\n".join(names))
    name = input("Table name: ").strip()
    if name not in names:
        raise ValueError("Choose an exact table name from the table list.")
    existing = tables.list_columns(database, name)
    print("Columns:\n" + "\n".join(existing))
    action = input("Column action (add/remove, blank to cancel): ").strip().lower()
    if not action:
        print("Modification cancelled.")
        return
    if action not in {'add', 'remove'}:
        raise ValueError("Choose add or remove.")
    additions = {}
    removals = []
    if action == 'add':
        print("Types: INT, BIGINT, FLOAT, DOUBLE, BOOLEAN, DATE, DATETIME, "
              "TIMESTAMP, TEXT, VARCHAR(n), DECIMAL(p, s).")
    while True:
        column = input(f"Column to {action} (blank to finish): ").strip()
        if not column:
            break
        validate_identifier(column)
        selected = additions if action == 'add' else removals
        if column.lower() in {value.lower() for value in selected}:
            raise ValueError("Each column can only be selected once.")
        if action == 'add':
            if column.lower() in {value.lower() for value in existing}:
                raise ValueError("This column already exists.")
            additions[column] = input("Column type: ").strip()
        else:
            if column not in existing:
                raise ValueError("Choose an exact column name from the column list.")
            removals.append(column)
    if not additions and not removals:
        print("No columns selected. Modification cancelled.")
        return
    if action == 'add':
        tables.add_columns(database, name, additions)
    else:
        if len(removals) >= len(existing):
            raise ValueError("At least one column must remain in the table.")
        print(f"Permanently remove columns {', '.join(removals)} from "
              f"'{database}.{name}', including their stored data.")
        if input("Type REMOVE to apply, or anything else to cancel: ") != 'REMOVE':
            print("Modification cancelled.")
            return
        tables.drop_columns(database, name, removals)
    print(f"Table '{database}.{name}' updated successfully.")


def add_random_rows(db, tables):
    """Collect generated, repeated, or manually entered column values."""
    database = read_existing_database(db)
    names = tables.list_tables(database)
    if not names:
        print("No tables visible. Create a table first with option 5.")
        return
    print("Tables:\n" + "\n".join(names))
    name = input("Table name: ").strip()
    if name not in names:
        raise ValueError("Choose an exact table name from the table list.")
    columns = tables.column_types(database, name)
    print("Columns:\n" + "\n".join(f"{column}: {kind}" for column, kind in columns.items()))
    count = int(input("Number of rows: ").strip())
    if count <= 0:
        raise ValueError("Number of rows must be positive.")
    ranges = {}
    values = {}
    row_values = {}
    while True:
        column = input("Column to fill (blank to finish): ").strip()
        if not column:
            break
        if column not in columns:
            raise ValueError("Choose an exact column name from the column list.")
        if column in ranges or column in values or column in row_values:
            raise ValueError("Each column can only be selected once.")
        parser = ColumnValues(columns[column])
        default_mode = 'range' if parser.numeric else 'fixed'
        modes = {'manual', 'fixed', 'range'} if parser.numeric else {'manual', 'fixed'}
        while True:
            mode = input(
                f"Fill mode for {column} ({'/'.join(sorted(modes))}) [{default_mode}]: "
            ).strip().lower() or default_mode
            if mode in modes:
                break
            print("Choose one of: " + ", ".join(sorted(modes)))
        if mode == 'manual':
            entries = []
            for index in range(count):
                while True:
                    value = input(f"Value for {column}, row {index + 1}/{count}: ")
                    try:
                        parser.parse(value)
                    except ValueError as error:
                        print(f"Invalid value: {error}")
                    else:
                        entries.append(value)
                        break
            row_values[column] = entries
        elif mode == 'range':
            minimum = parser.parse(input(f"Minimum for {column}: ").strip())
            maximum = parser.parse(input(f"Maximum for {column}: ").strip())
            parser.generator((minimum, maximum))
            ranges[column] = (minimum, maximum)
        else:
            print("Enter a value repeated in every row (dates: YYYY-MM-DD; "
                  "date/times: YYYY-MM-DD HH:MM:SS).")
            value = input(f"Value for {column}: ")
            parser.parse(value)
            values[column] = value
    if row_values:
        tables.insert_random_rows(database, name, count, ranges,
                                  values=values, row_values=row_values)
    elif values:
        tables.insert_random_rows(database, name, count, ranges, values=values)
    else:
        tables.insert_random_rows(database, name, count, ranges)
    print(f"Inserted {count} row(s) into '{database}.{name}'.")


def edit_row_values(db, tables):
    """Select a column and enter its value for each existing row."""
    database = read_existing_database(db)
    names = tables.list_tables(database)
    if not names:
        print("No tables visible. Create a table first with option 5.")
        return
    print("Tables:\n" + "\n".join(names))
    name = input("Table name: ").strip()
    if name not in names:
        raise ValueError("Choose an exact table name from the table list.")
    keys = tables.primary_key_columns(database, name)
    if not keys:
        raise ValueError("Editing existing rows requires a table with a primary key.")
    types = tables.column_types(database, name)
    while True:
        columns, rows = tables.read_table(database, name)
        if not rows:
            print("Table is empty. Add rows first with option 8.")
            return
        print("Editable columns:\n" + '\n'.join(
            f"{column}: {kind}" for column, kind in types.items()))
        column = input("Column to change (blank to finish): ").strip()
        if not column:
            return
        if column not in types:
            print("Choose an exact name from the editable column list.")
            continue
        parser = ColumnValues(types[column])
        print("Enter a new value for each row, or leave blank to keep its current value.")
        saved = 0
        for index, row in enumerate(rows, 1):
            current = dict(zip(columns, row))
            print(f"Row {index}/{len(rows)}: " + ', '.join(
                f"{name}={value!r}" for name, value in current.items()))
            while True:
                value = input(f"New value for {column} (blank to keep): ")
                if value == '':
                    break
                try:
                    parsed = parser.parse(value)
                except ValueError as error:
                    print(f"Invalid value: {error}")
                    continue
                tables.update_row(database, name,
                                  {key: current[key] for key in keys}, {column: parsed})
                saved += 1
                break
        print(f"Saved '{column}' values for {saved} row(s) in '{database}.{name}'.")


def modify_database(db):
    """Prompt for, confirm, and update a database's defaults."""
    name = read_existing_database(db)
    print(
        "Changes defaults for new tables only; existing tables and data "
        "are not converted."
    )
    charset = input("New character set (e.g. utf8mb4): ").strip()
    collation = input("New collation (e.g. utf8mb4_unicode_ci): ").strip()
    print(
        f"Change '{name}' to character set '{charset}' "
        f"and collation '{collation}'."
    )
    if input("Type MODIFY to apply, or anything else to cancel: ") != "MODIFY":
        print("Modification cancelled.")
        return
    db.modify_database(name, charset, collation)
    print(f"Database '{name}' defaults updated successfully.")


def delete_database(db):
    """Prompt for and confirm permanent database deletion."""
    name = read_existing_database(db)
    print(
        f"Permanently delete '{name}' and all its tables and data. "
        "This cannot be undone by the app."
    )
    confirmation = input(
        f"Type DELETE {name} to confirm, or anything else to cancel: "
    )
    if confirmation != f"DELETE {name}":
        print("Deletion cancelled.")
        return
    db.delete_database(name)
    print(f"Database '{name}' deleted successfully.")


def handle_menu_choice(db, tables, choice):
    """Run one menu action; return False when the application should exit."""
    actions = {
        "1": list_databases,
        "2": create_database,
        "3": modify_database,
        "4": delete_database,
        "5": lambda db: create_table(db, tables),
        "6": lambda db: list_tables(db, tables),
        "7": lambda db: view_table(db, tables),
        "8": lambda db: add_random_rows(db, tables),
        "9": lambda db: modify_table(db, tables),
        "10": lambda db: edit_row_values(db, tables),
    }
    if choice == "0":
        return False
    action = actions.get(choice)
    if action is None:
        print("Choose 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, or 0.")
    else:
        action(db)
    return True


def run_menu(db, tables):
    """Navigate database and table sections until the user exits."""
    section = None
    while True:
        print({None: MENU, '1': DATABASE_MENU, '2': TABLE_MENU}[section])
        choice = input("Choose an option: ").strip()
        if choice == '0':
            if section is None:
                return
            section = None
            continue
        if section is None:
            if choice in {'1', '2'}:
                section = choice
            else:
                print("Choose 1, 2, or 0.")
            continue
        allowed = {'1', '2', '3', '4'} if section == '1' else {'5', '6', '7', '8', '9', '10'}
        if choice not in allowed:
            print("Choose an option from this section, or 0 to return to the main menu.")
            continue
        try:
            handle_menu_choice(db, tables, choice)
        except (ValueError, RuntimeError, mysql.connector.Error) as err:
            print(f"Operation failed: {err}")


def run_application():
    """Run the CLI, clean up its connection, and return an exit status."""
    manager = ConnectionManager()
    db = DatabaseOperations(manager)
    tables = TableOperations(manager)
    try:
        print("MySQL Database Creator")
        connect_to_server(manager)
        print("Connected successfully.")
        run_menu(db, tables)
        return 0
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return 0
    finally:
        manager.close()
