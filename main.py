"""Interactive MySQL database creator."""

from getpass import getpass

import mysql.connector

from ConnManager import ConnectionManager


def read_port():
    """Prompt for a valid TCP port, using 3306 when the input is blank."""
    while True:
        # Strip surrounding spaces; an empty answer selects the default port.
        value = input("Port [3306]: ").strip() or "3306"
        # Check the text before converting it to an integer and checking its range.
        if value.isascii() and value.isdecimal() and 1 <= int(value) <= 65535:
            return int(value)
        print("Enter a port between 1 and 65535.")


def main():
    """Run the menu, clean up the connection, and return the handled exit status."""
    # Keep database access in the manager and user interaction in this module.
    db = ConnectionManager()
    try:
        print("MySQL Database Creator")
        host = input("Host [localhost]: ").strip() or "localhost"
        port = read_port()
        user = input("Username [root]: ").strip() or "root"
        # getpass hides the password as it is typed in a supported terminal.
        password = getpass("Password: ")
        db.connect(host, user, password, port)
        print("Connected successfully.")

        # Reuse the connection until the user exits or interrupts the program.
        while True:
            print("\n1. List databases\n2. Create database\n0. Exit")
            choice = input("Choose an option: ").strip()
            try:
                if choice == "1":
                    names = db.list_databases()
                    # Join the returned names with newlines for one database per line.
                    print("\n".join(names) if names else "No databases visible.")
                elif choice == "2":
                    name = input("New database name: ").strip()
                    db.create_database(name)
                    print(f"Database '{name}' created successfully.")
                elif choice == "0":
                    # Returning still runs the finally block that closes the connection.
                    return 0
                else:
                    print("Choose 1, 2, or 0.")
            except (ValueError, RuntimeError, mysql.connector.Error) as err:
                # Show validation/connection/SQL errors and let the user try again.
                print(f"Operation failed: {err}")
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
