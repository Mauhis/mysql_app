# Developer guide

[Back to README](../README.md)

## Architecture

`cli.py` owns terminal interaction: it gathers credentials, validates the port,
connects once, and dispatches menu operations. It catches expected operation
errors so the menu can continue, and calls `close()` in a `finally` block.
`main.py` is the executable entry point and delegates to `run_application()`.
Its `if __name__ == "__main__"` guard allows importing it without starting prompts.

`ConnManager.py` owns the connector connection and SQL execution. It does not
prompt, print, or suppress database errors. Each database operation opens a
cursor and closes it in `finally`. The caller owns connection cleanup.
`DatabaseOperations` and `TableOperations` receive the same manager and build
their SQL in `database_operations.py` and `table_operations.py`. Shared name
validation lives in `validation.py`. These classes do not own or close the connection.

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

### `DatabaseOperations(manager).list_databases()`

Executes `SHOW DATABASES` and returns a list of database name strings visible to
the account. The app performs no additional sorting or filtering. Raises
`RuntimeError` when no live connection is available; connector errors propagate.
The cursor is closed whether SQL execution succeeds or fails.

### `DatabaseOperations(manager).create_database(name)`

Accepts a string matching `[A-Za-z_][A-Za-z0-9_]{0,63}` and returns `None` after
successful execution. It preserves the supplied name, including case, and does
not strip whitespace. The CLI strips surrounding whitespace before calling it.

Raises `ValueError` for a string that fails validation, `RuntimeError` for a
valid name when disconnected, or `mysql.connector.Error` for server/connector
errors such as duplicate names and insufficient permissions. Non-string names also raise `ValueError`.

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

## Modification and deletion API

`validation.validate_identifier(name, protect_system=False)` validates the shared name
rule. When protection is enabled, the four standard MySQL system databases are
rejected case-insensitively with `ValueError`.

`DatabaseOperations.modify_database(name, charset, collation)` executes `ALTER DATABASE` to change
both defaults. Option strings must begin with an ASCII letter and contain only
ASCII letters, digits, or underscores, up to 64 characters. MySQL checks support
and compatibility. Existing tables and data are not converted.

`DatabaseOperations.delete_database(name)` executes `DROP DATABASE` without `IF EXISTS`, so a missing
database raises a server error. This permanently removes the database contents.

Both methods validate identifiers and protect system databases before opening a
cursor. Disconnected operations raise `RuntimeError`; connector errors propagate,
and cursors close on success or failure. They do not prompt: programmatic callers
must obtain their own confirmation. The CLI checks visibility and requires exact
confirmation before calling either method. The server remains authoritative if a
database disappears between the visibility check and execution.

## Reusing the manager

Run this example from the project directory after installing requirements. It
creates an actual database and prompts for credentials. Use an account permitted
to create the example database and change the name if it already exists.

```python
from getpass import getpass

import mysql.connector

from ConnManager import ConnectionManager
from database_operations import DatabaseOperations
from table_operations import TableOperations

manager = ConnectionManager()
databases = DatabaseOperations(manager)
tables = TableOperations(manager)
try:
    manager.connect(
        host="localhost",
        port=3306,
        user=input("MySQL username: "),
        password=getpass("MySQL password: "),
    )
    databases.create_database("example_app")
    tables.create_table("example_app", "users", {"id": "INT"}, primary_key="id")
    for name in databases.list_databases():
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

`run_application()` runs the interactive session and returns `0` after a menu exit or
handled `KeyboardInterrupt`/`EOFError`, and `1` after an initial connector error.
Expected errors inside the menu are displayed without terminating the loop.
`main()` delegates to it, and `SystemExit(main())` translates the return value to
the process exit status.
Cleanup errors and other unexpected exceptions can still propagate.

## Automated verification

From the project directory, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

The tests in `tests/test_connection_manager.py` and
`tests/test_database_changes.py` use `unittest` and mocks.
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
validate authentication, server permissions, server compatibility, real terminal behavior. Menu tests mock user input and verify confirmation,
cancellation, and interruption. The requirements file specifies a dependency
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

For cleanup, select **4**, enter the disposable database name, and confirm the
exact deletion phrase after verifying the target.

## Extending the application

Keep prompts in `cli.py`, the executable entry point in `main.py`, and reusable
database logic in `database_operations.py`, table logic in `table_operations.py`,
and connection lifecycle in `ConnManager.py`.
For new operations, close cursors on both success and failure, propagate useful
errors to callers, and test failure behavior as well as successful execution.
Use connector parameter binding for data values and deliberate validation for
identifiers.

Potential additions include selecting a database, exposing
connection security options, and adding non-interactive commands. Each requires
implementation and documentation; none is currently available. Any future
non-interactive interface should define exit statuses for failed operations
instead of relying on the current menu's successful exit status.

Additional manual checks: modify a disposable database's defaults with option 3,
check cancellation before trying `MODIFY`, and inspect the resulting defaults with
your administration tool. Try an incompatible charset/collation and verify an
error. Cancel deletion once before confirming deletion of the disposable database,
then list databases to verify removal. Mock tests cover these control paths but
do not verify behavior against a live server.

## Table creation API

`TableOperations(manager).create_table(database, name, columns, primary_key=None)` creates one table in
an explicitly named database without changing the connection's default database.
`columns` is a nonempty dictionary mapping names to type strings, in column order.
See [Create tables](../README.md#create-tables) for supported types and an example.
`VARCHAR` accepts lengths 1–65535; `DECIMAL` accepts precision 1–65 and scale
0–30 no greater than precision. MySQL enforces further storage and key limits.

Invalid names, duplicate column names ignoring case, unsupported types, and an
unknown primary key raise `ValueError` before opening a cursor. System databases
are rejected. A primary key must match a dictionary key exactly.
Disconnected calls raise `RuntimeError`; connector errors propagate and cursors
close on success or failure. Success returns `None`. Existing tables are not
replaced or silently skipped. Table creation takes effect immediately.

`tests/test_table_creation.py` covers SQL generation, rejected schemas, disconnected
calls, cursor cleanup, and menu creation and error recovery with mocked connections.

## Adding columns and row values

`TableOperations(manager).add_columns(database, name, columns)` adds columns to
an existing table with one ALTER TABLE statement. It uses the same dictionary,
identifier validation, and supported types as `create_table()`. Existing column
names cause a server error. Schema changes take effect immediately.

`TableOperations(manager).insert_row(database, name, values)` inserts one row
using a nonempty dictionary of column names to Python values. Names must be valid
and unique ignoring case. Values are bound as SQL parameters, including `None`
for NULL. Omitted columns use server defaults; MySQL checks types and constraints.
The method commits on success and rolls back on execution or commit failure.
Commit and rollback affect the connection's entire current transaction, so avoid
mixing this API with unrelated pending writes on the shared connection.
Both methods return `None` on success and reject system databases.

## Shared SQL execution and migration

`ConnectionManager.execute(statement, *, fetch=False, params=None, commit=False)` executes SQL and always closes
its cursor. With `fetch=True` it returns all result rows; otherwise it returns
`None`. Optional `params` are passed separately to the connector. With
`commit=True`, success commits and failure rolls back the current transaction;
otherwise transaction handling is left to the caller. Operation classes validate
interpolated identifiers before using it.

Database and table methods have moved off `ConnectionManager`. Existing callers
should construct `DatabaseOperations(manager)` and `TableOperations(manager)` and
call the corresponding methods there, as in the example above. Connection setup
and cleanup remain on the manager. The interactive menu is unchanged.

### Manual column values

`TableOperations.insert_random_rows(database, name, count, ranges, values=None,
*, row_values=None)` accepts per-column lists or tuples through `row_values`.
Each sequence must have exactly `count` entries in row order. Columns cannot
appear in more than one of `ranges`, `values`, and `row_values`. All manual
entries are parsed against the schema before the batch is inserted.
CLI option 8 offers `manual`, `fixed`, and (for numeric columns) `range` modes.
Manual input retries invalid values at the current row.

## Modify existing table columns

Choose **9 — Modify table columns**, select an existing database and table,
then choose `add` or `remove`.

- **add:** enter each new column name and its type (for example, `email` and
  `VARCHAR(100)`). Leave the column prompt blank to apply the additions.
- **remove:** select existing column names, leave the prompt blank, and type
  `REMOVE` to permanently delete those columns and their stored data.

An empty selection cancels. At least one column must remain. New columns use
MySQL defaults; the same types as table creation are supported. Changes require
ALTER permission and take effect immediately. The server checks dependencies
and constraints; errors return to the menu.

Python API (no interactive confirmation):

```python
tables.add_columns("demo_app", "people", {"email": "VARCHAR(100)", "age": "INT"})
tables.drop_columns("demo_app", "people", ["email", "age"])
```

`drop_columns()` accepts a nonempty list or tuple of exact existing names.
Both methods validate identifiers, reject duplicate names regardless of case,
and protect system databases. Each call executes one ALTER TABLE statement.
