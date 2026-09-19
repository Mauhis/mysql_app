"""Interactive MySQL database creator."""

from getpass import getpass

import mysql.connector

from ConnManager import ConnectionManager


MENU = (
    "\n1. List databases\n2. Create database\n"
    "3. Modify database defaults\n4. Delete database\n0. Exit"
)


def read_port():
    """Prompt for a valid TCP port, using 3306 when the input is blank."""
    while True:
        # Strip surrounding spaces; an empty answer selects the default port.
        value = input("Port [3306]: ").strip() or "3306"
        # Check the text before converting it to an integer and checking its range.
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


def read_existing_database(db):
    """Return a validated, visible database selected by the user."""
    name = input("Existing database name: ").strip()
    db.validate_database_name(name, protect_system=True)
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


def handle_menu_choice(db, choice):
    """Run one menu action; return False when the application should exit."""
    actions = {
        "1": list_databases,
        "2": create_database,
        "3": modify_database,
        "4": delete_database,
    }
    if choice == "0":
        return False
    action = actions.get(choice)
    if action is None:
        print("Choose 1, 2, 3, 4, or 0.")
    else:
        action(db)
    return True


def run_menu(db):
    """Run menu actions until the user chooses to exit."""
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        try:
            if not handle_menu_choice(db, choice):
                return
        except (ValueError, RuntimeError, mysql.connector.Error) as err:
            print(f"Operation failed: {err}")


def main():
    """Run the menu, clean up the connection, and return the handled exit status."""
    # Keep database access in the manager and user interaction in this module.
    db = ConnectionManager()
    try:
        print("MySQL Database Creator")
        connect_to_server(db)
        print("Connected successfully.")
        run_menu(db)
        return 0
    except mysql.connector.Error as err:
        # A failed initial connection prevents entering the menu; report failure status.
        print(f"Connection failed: {err}")
        return 1
    except (KeyboardInterrupt, EOFError):
        # Handle Ctrl+C and end-of-input without displaying a traceback.
        print("\nExiting.")
        return 0
    finally:
        # Release the connection on normal exit and when an exception leaves the loop.
        db.close()


if __name__ == "__main__":
    # Run only when launched directly; use main's return value as the exit status.
    raise SystemExit(main())
