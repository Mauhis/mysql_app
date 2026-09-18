# Developer guide

[Back to README](../README.md)

## Architecture

`main.py` owns terminal interaction: it gathers credentials, validates the port,
connects once, and dispatches menu operations. It catches expected operation
errors so the menu can continue, and calls `close()` in a `finally` block.
The `if __name__ == "__main__"` guard allows importing it without starting prompts.

`ConnManager.py` owns the connector connection and SQL execution. It does not
prompt, print, or suppress database errors. Each database operation opens a
cursor and closes it in `finally`. The caller owns connection cleanup.

The application connects at server level without choosing a default database.
Creating a database does not select it for later queries. There is no connection
pool, automatic reconnect, retry policy, migration layer, or table model.

## ConnectionManager API

Import with `from ConnManager import ConnectionManager`.

### `ConnectionManager()`

Creates a manager with `connection = None`. Construction does not contact a
server. Treat `connection` as implementation state; use the methods below to
manage its lifecycle.

### `connect(host, user, password, port=3306)`

Closes an existing connection before calling `mysql.connector.connect()` with
those arguments and `connection_timeout=10`. Returns `None` on success and stores
the new connection. Connector failures propagate to the caller. If connecting
fails after successful cleanup, the manager remains disconnected.

This method does not implement the CLI's port validation or input trimming.
Programmatic callers should provide appropriate connector argument types and
values. Reconnecting replaces the existing session, even if the new connection
attempt subsequently fails.

### `list_databases()`

Executes `SHOW DATABASES` and returns a list of database name strings visible to
the account. The app performs no additional sorting or filtering. Raises
`RuntimeError` when no live connection is available; connector errors propagate.
The cursor is closed whether SQL execution succeeds or fails.

### `create_database(name)`

Accepts a string matching `[A-Za-z_][A-Za-z0-9_]{0,63}` and returns `None` after
successful execution. It preserves the supplied name, including case, and does
not strip whitespace. The CLI strips surrounding whitespace before calling it.

Raises `ValueError` for a string that fails validation, `RuntimeError` for a
valid name when disconnected, or `mysql.connector.Error` for server/connector
errors such as duplicate names and insufficient permissions. Non-string input
is outside the method's contract and may raise `TypeError`.

Validation occurs before opening the cursor. SQL value placeholders cannot
represent database identifiers, so the implementation validates the restricted
identifier and wraps it in backticks before interpolation. Retain validation
when extending SQL construction. New databases use `utf8mb4` and
`utf8mb4_unicode_ci`. Creation is immediate and is not undone by closing the
connection; no separate application commit call is used.

### `close()`

Closes the connection if present and clears the reference to `None`, even if
connector cleanup raises. Repeated calls after cleanup are safe. Cleanup errors
are allowed to propagate.

### `_cursor()` (internal)

Checks that a connection exists and `is_connected()` is true, then returns a
new cursor. Raises `RuntimeError` if disconnected. Public operations use this
helper; callers should not need it.

## Reusing the manager

Run this example from the project directory after installing requirements. It
creates an actual database and prompts for credentials. Use an account permitted
to create the example database and change the name if it already exists.

```python
from getpass import getpass

import mysql.connector

from ConnManager import ConnectionManager

manager = ConnectionManager()
try:
    manager.connect(
        host="localhost",
        port=3306,
        user=input("MySQL username: "),
        password=getpass("MySQL password: "),
    )
    manager.create_database("example_app")
    for name in manager.list_databases():
        print(name)
except (ValueError, RuntimeError, mysql.connector.Error) as error:
    print(f"Database operation failed: {error}")
finally:
    manager.close()
```

## CLI functions

`read_port()` repeatedly prompts until it receives an ASCII decimal integer in
`1..65535`; blank input selects `3306`. It returns an integer. Input interruption
propagates to the outer `main()` handler.

`main()` runs the interactive session and returns `0` after a menu exit or
handled `KeyboardInterrupt`/`EOFError`, and `1` after an initial connector error.
Expected errors inside the menu are displayed without terminating the loop.
`SystemExit(main())` translates the return value to the process exit status.
Cleanup errors and other unexpected exceptions can still propagate.

## Automated verification

From the project directory, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

The seven tests in `tests/test_connection_manager.py` use `unittest` and mocks.
They cover:

- SQL construction for a valid database name.
- Rejection of invalid names before cursor creation, including an SQL injection
  attempt and an overlong identifier.
- Conversion of database rows into a list of names.
- Error propagation and cursor cleanup after SQL execution fails.
- Rejection of operations when disconnected.
- Repeatable connection cleanup.
- Cleanup of the old connection when a replacement connection attempt fails.

No test requires credentials or contacts a real MySQL server. These tests do not
validate authentication, server permissions, server compatibility, terminal
behavior, or the interactive menu. The requirements file specifies a dependency
range rather than an exact lock; record the installed connector version when
reporting version-specific behavior.

## Manual verification against MySQL

Use a development server and an account with permission to create a disposable
database. Database creation persists after the application exits.

1. Start the app and connect with the development account.
2. Select **1** and check the visible database list.
3. Select **2** and create a unique name such as `manual_check_20260918`.
4. List databases again and confirm the new name appears.
5. Try creating the same name again; confirm an error and a usable menu.
6. Try an invalid name such as `bad-name`; confirm the validation message.
7. Exit with **0**, restart, and check Ctrl+C exits cleanly.
8. Separately try incorrect connection details and confirm a connection error.

The app has no delete command. If cleanup is needed, remove only the disposable
database using your usual administration tool after verifying its name.

## Extending the application

Keep prompts in `main.py` and reusable database logic in `ConnectionManager`.
For new operations, close cursors on both success and failure, propagate useful
errors to callers, and test failure behavior as well as successful execution.
Use connector parameter binding for data values and deliberate validation for
identifiers.

Potential additions include selecting a database, creating tables, exposing
connection security options, and adding non-interactive commands. Each requires
implementation and documentation; none is currently available. Any future
non-interactive interface should define exit statuses for failed operations
instead of relying on the current menu's successful exit status.
