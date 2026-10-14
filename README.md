# MySQL Database Creator

This project was developed solely using AI for experimental purposes.

Its main purpose is to provide a quick way to create MySQL databases, tables,
and sample data that recreate the database examples given in LeetCode SQL
questions, so you can practice solving them locally.

A Python desktop and command-line application for connecting to an existing
MySQL server, listing visible databases, creating empty databases, changing database defaults,
deleting databases, creating tables, and browsing table contents.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Database names and creation behavior](#database-names-and-creation-behavior)
- [Modify or delete existing databases](#modify-or-delete-existing-databases)
- [Create tables](#create-tables)
- [Edit existing row values](#edit-existing-row-values)
- [Use the classes in Python](#use-the-classes-in-python)
- [Troubleshooting](docs/troubleshooting.md)
- [Developer guide and API reference](docs/development.md)
- [Project layout](#project-layout)
- [License](#license)

## Requirements

- Python 3.10 or newer, with `pip` and virtual environment support.
- An existing, running MySQL server reachable from your machine.
- A MySQL account authorized to connect from your machine and create the intended
  databases and tables. Modification requires ALTER permission; deletion requires
  DROP permission. Ask your database administrator for an appropriate account.
- The `mysql-connector-python` dependency declared in `requirements.txt`.

The application does not install or start MySQL. It creates databases and tables;
The Python API also adds columns and inserts rows; it does not run migrations or rename databases.
The desktop interface uses Tkinter; the terminal interface remains available with `--cli`.

## Installation

Run these commands from the project directory.

### Linux and macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### Windows PowerShell

Activation is optional; you can run the virtual environment's Python directly:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

For later sessions on Linux or macOS, run `.venv/bin/python main.py` from the
project directory, or activate the environment again and run `python main.py`.

## Desktop interface

Run `python main.py` to open the desktop window. Enter the MySQL connection
settings and click **Connect**. Select a database to see its tables, then select
a table to browse its data.

- **New database** creates and selects a practice database.
- **Create table** accepts a table name and column definitions such as
  `id:INT; name:VARCHAR(100); price:DECIMAL(10, 2)`, plus an optional primary key.
- **Add row** accepts typed values; blank fields use server defaults.
- **Edit selected row** (or double-click a row) changes its values. A primary key
  is required; unchanged fields are preserved.
- **Add column** adds a column to the selected table. Use row editing to fill it.
- **Delete column** selects an existing column and asks for confirmation before
  permanently removing it and its values. At least one column must remain;
  server dependencies may prevent deletion. Requires ALTER permission.
- **Refresh** reloads the database and table lists.

Database calls run in the background. The grid loads all rows, so this interface
is intended for small practice datasets. Row dialogs support the same value types
as the terminal interface; they do not currently provide an explicit SQL NULL input.

Tkinter is included with many Python installations. On Debian/Ubuntu, install
`python3-tk` if it is missing. To use the terminal interface instead, run:

```bash
python main.py --cli
```

## Usage (terminal interface)

### Connect to a server

The application asks for connection details before showing the menu:

| Prompt | Default | Notes |
| --- | --- | --- |
| Host | `localhost` | Hostname or IP address of the MySQL server. |
| Port | `3306` | An integer from 1 to 65535; invalid input prompts again. |
| Username | `root` | Enter your assigned MySQL account. |
| Password | None | Enter the account password; terminal input is hidden. |

Press Enter to accept a default. Host, username, port, and database name input
have surrounding whitespace removed; the password is passed through unchanged.
A connection attempt uses a 10-second connection timeout. If connecting fails,
the program prints `Connection failed:` with the connector error and exits.

Credentials are entered on each run and are not saved to disk by the application.
Use a terminal that supports hidden password entry. The app does not read `.env`
files, environment variables, configuration files, or command-line options.
Transport security settings are not exposed by the app; connection options other
than those in `ConnectionManager.connect()` use the connector's defaults.

### Choose an operation

The main menu separates operations into two sections:

```text
Main menu
1. Database actions
2. Table actions
0. Exit
```

Choose **1** for database operations or **2** for table operations. After each
operation you remain in its section. Choose **0** within either section to
return to the main menu, where you can switch sections or exit.

```text
Database actions
1. List databases
2. Create database
3. Modify database defaults
4. Delete database
0. Return to main menu

Table actions
5. Create table
6. List tables
7. View table contents
8. Add typed rows
9. Modify table columns
10. Edit existing row values
0. Return to main menu
```

- **1 — List databases:** prints one visible database name per line. Visibility
  depends on the connected account's permissions. An empty result prints
  `No databases visible.`
- **2 — Create database:** asks for a name and creates the database immediately.
  Successful creation prints a confirmation and returns to the menu.
- **3 — Modify database defaults:** changes the character set and collation
  after exact confirmation with `MODIFY`.
- **4 — Delete database:** removes a database and its contents after exact
  confirmation with `DELETE database_name`.
- **5 — Create table:** asks for an existing database, table name, column names
  and types, and an optional primary key.
- **6 — List tables:** asks for a database and lists its visible tables and views.
- **7 — View table contents:** lists tables in a database, then asks which table
  to display. Prints column headings, all rows, and a row count. Empty tables
  are reported explicitly. SQL NULL prints as `NULL`; text values are quoted.
  Reading requires SELECT permission. All rows are loaded into memory, so use
  this option for tables small enough to display in your terminal.
- **10 — Edit existing row values:** selects a column and prompts for its value
  in each existing row, including newly added columns. Requires a primary key.
- **0:** returns to the main menu from a section; exits and closes the connection
  when selected at the main menu.

Invalid choices show a prompt and keep you in the current menu. Operation errors
print `Operation failed:` and allow another choice. There is no automatic
reconnect; if the connection is lost, exit and restart the application.

### Example session

This example assumes a server account named `db_creator` with permission to
create `demo_app`. The password is entered without being displayed.

```text
MySQL Database Creator
Host [localhost]: localhost
Port [3306]: 3306
Username [root]: db_creator
Password:
Connected successfully.

Main menu
1. Database actions
2. Table actions
0. Exit
Choose an option: 1

Database actions
1. List databases
2. Create database
3. Modify database defaults
4. Delete database
0. Return to main menu
Choose an option: 2
New database name: demo_app
Database 'demo_app' created successfully.

Database actions
1. List databases
2. Create database
3. Modify database defaults
4. Delete database
0. Return to main menu
Choose an option: 0

Main menu
1. Database actions
2. Table actions
0. Exit
Choose an option: 0
```

Ctrl+C or end-of-input also exits and runs connection cleanup. Normal menu exit
and handled interruption return exit status `0`; an initial connector failure
returns `1`. A failed menu operation does not by itself set a nonzero exit status.
Unexpected exceptions, including cleanup failures, are not covered by those
handled exit paths.

## Database names and creation behavior

Names must satisfy the application's naming rule:

- Between 1 and 64 characters.
- Start with an ASCII letter or underscore.
- Contain only ASCII letters, digits, and underscores.

Valid examples: `demo_app`, `_scratch`, `Project2026`.
Invalid examples: `2026_project`, `my-app`, `my app`, or an empty name.
This is a deliberately restricted application rule, not the full set of names
that MySQL may accept.

New databases use the `utf8mb4` character set and `utf8mb4_unicode_ci` collation.
The application sends the following SQL after validating the name:

```sql
CREATE DATABASE `demo_app` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
```

Creation takes effect immediately; exiting does not undo it. Existing names
produce a server error because the app does not use `IF NOT EXISTS`. Creation never overwrites an existing database. Database name case behavior is determined by
the server; the app preserves the entered case.

## Modify or delete existing databases

Use **1** to find the exact name, then **3** to change defaults or **4** to delete.
Both operations require a visible database with a name satisfying the app's naming
rule. The app blocks changes to `mysql`, `sys`, `information_schema`, and
`performance_schema`, including case variants.

**Modify:** enter a character set and matching collation supported by your server
(for example, `utf8mb4` and `utf8mb4_unicode_ci`). Review the proposed values and
type `MODIFY` exactly to apply them. Any other response cancels. Both values are
required. The server rejects unknown or incompatible values. This changes the
database defaults used by new tables; it does not rename the database or convert
existing tables or data. See the [MySQL ALTER DATABASE reference](https://dev.mysql.com/doc/refman/8.0/en/alter-database.html)
and [database character set documentation](https://dev.mysql.com/doc/refman/8.0/en/charset-database.html).

**Delete:** review the target and type `DELETE database_name` exactly, substituting
the displayed name. Any other response cancels. Deletion permanently removes the
database and its tables and data; the app cannot undo it. Back up needed data first.

The account needs ALTER permission for modification and DROP permission for
deletion. Server errors return you to the menu. Changes take effect immediately.

## Create tables

Choose **5**, enter an existing database and a new table name, then enter each
column name and type. Leave the column name blank to finish, and optionally
enter one column name as the primary key. At least one column is required.

Supported types are `INT`, `BIGINT`, `FLOAT`, `DOUBLE`, `BOOLEAN`, `DATE`,
`DATETIME`, `TIMESTAMP`, `TEXT`, `VARCHAR(n)`, and `DECIMAL(p, s)`.
Names follow the same rules as database names. Column names must be unique
regardless of case. The server checks additional limits, such as row size.
Primary key columns are non-nullable; other columns use MySQL defaults.
Auto-increment, custom defaults, and foreign keys are not currently exposed.

Creation is immediate and requires CREATE permission on the target database.
Existing tables produce an error and are never replaced. System databases
are protected. New tables inherit the database character set and collation.

To add columns and insert row values from Python:

```python
tables.add_columns("demo_app", "products", {"stock": "INT"})
tables.insert_row(
    "demo_app", "products",
    {"id": 1, "name": "Notebook", "price": "4.50", "stock": 20},
)
```

`add_columns()` defines new columns on an existing table using the supported SQL
types above. `insert_row()` accepts a nonempty dictionary of column names and
values, uses SQL parameters, and commits the insert. Use `None` for SQL NULL;
omitted columns use server defaults. These methods are available through the
Python API. Column additions require ALTER permission and inserts require INSERT
permission. Both methods reject system databases and propagate server errors.

For reading from Python, `tables.list_tables("demo_app")` returns table/view
names. `columns, rows = tables.read_table("demo_app", "products")` returns column
names and all row tuples, with SQL NULL represented by `None`. Read operations
use the same identifier rules and allow system databases when permissions permit.

## Use the classes in Python

Database and table operations use separate classes that share one
`ConnectionManager`. The manager opens and closes the connection and executes
SQL; operation classes build and validate their statements. Prompts and
confirmations belong to `cli.py`.

Run this example from the project directory. It creates a real database and
table, so use new names and an account with the required permissions.

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
        user=input("MySQL username: "),
        password=getpass("MySQL password: "),
    )
    databases.create_database("demo_app")
    tables.create_table(
        "demo_app",
        "products",
        {"id": "INT", "name": "VARCHAR(100)", "price": "DECIMAL(10, 2)"},
        primary_key="id",
    )
    print(databases.list_databases())
except (ValueError, RuntimeError, mysql.connector.Error) as error:
    print(f"Operation failed: {error}")
finally:
    manager.close()
```

| Class or module | Responsibility |
| --- | --- |
| `ConnectionManager` | `connect()`, `execute()`, and `close()`; connection and cursor cleanup. |
| `DatabaseOperations` | `list_databases()`, `create_database()`, `modify_database()`, and `delete_database()`. |
| `TableOperations` | `list_tables()`, `read_table()`, `create_table()`, `add_columns()`, and `insert_row()`. |
| `validation` | Shared `validate_identifier()` and `validate_sql_name()` functions. |

Database and table methods are no longer on `ConnectionManager`. Update older
calls such as `manager.create_database(...)` to `databases.create_database(...)`
and `manager.create_table(...)` to `tables.create_table(...)`.
Both operation objects use the manager's current connection; neither opens or
closes its own connection. Programmatic operations do not prompt for confirmation.
See the [API reference](docs/development.md) for arguments and error behavior.

## Project layout

```text
mysql_app/
├── ConnManager.py                 # Connection lifecycle and SQL execution
├── database_operations.py         # DatabaseOperations
├── table_operations.py            # TableOperations
├── validation.py                  # Shared SQL name validation
├── cli.py                         # Interactive prompts and menu workflow
├── desktop.py                     # Tkinter desktop interface
├── main.py                        # Desktop entry point; --cli for terminal mode
├── requirements.txt               # MySQL connector dependency range
├── tests/
│   ├── test_connection_manager.py
│   ├── test_database_changes.py
│   └── test_table_creation.py
├── docs/
│   ├── development.md             # API, architecture, testing, extension points
│   └── troubleshooting.md         # Setup and runtime problems
├── README.md
└── LICENSE
```

To run the automated tests in an activated environment:

```bash
python -m unittest discover -s tests -v
```

Tests mock the connector and do not require a running MySQL server. See the
[developer guide](docs/development.md) for coverage and manual verification.

## License

This project's code is available under the [MIT License](LICENSE). Dependencies
retain their own licenses.

## Add typed rows

This option inserts new rows. To fill a newly added column in rows that already
exist, use **10 — Edit existing row values** instead.

Choose **8**, select an existing database and table, and enter the row count.
The app displays column names and their actual MySQL types. Select a column,
then choose `manual` to type a separate value for every row, `fixed` to repeat
one value, or `range` for generated numeric values. Press Enter at the mode
prompt to use `range` for numbers or `fixed` for other types.

For example, to insert five names into a `VARCHAR` column, enter a row count of
`5`, select `name`, and choose `manual`. Enter Alice, Bob, Carol, David, and Eve
at the five numbered prompts, then leave the column prompt blank to insert.
Invalid manual values prompt again for the same row. Text spacing is preserved.
Multiple manual columns use the same row order and can be combined with fixed
values and numeric ranges.

Supported values:

- Integer columns accept inclusive whole-number minimum and maximum values.
- FLOAT and DOUBLE columns accept fractional bounds.
- DECIMAL columns accept bounds that fit their precision and scale; generated
  values preserve the declared number of decimal places.
- CHAR, VARCHAR and TEXT columns accept text repeated in each new row.
- DATE accepts `YYYY-MM-DD`; DATETIME and TIMESTAMP accept
  `YYYY-MM-DD HH:MM:SS`, repeated in each new row.

Leave the column prompt blank to insert. Equal numeric bounds produce a fixed
value. Values may repeat, so unique keys can still cause an insertion failure.
Unsupported types are rejected. Generated columns are excluded; omit auto-increment
columns to let the server populate them. Other omitted columns need defaults or
must allow NULL. Server constraints, text byte limits, and temporal limits still
apply. Use option 7 to view the inserted rows.

```python
tables.insert_random_rows(
    "demo_app", "products", 10,
    {"stock": (0, 100), "price": ("1.50", "99.99")},
    values={"name": "Notebook"},
)
```

The batch uses parameterized SQL and one commit; failures roll back on
transactional tables such as InnoDB. `insert_rows()` and `insert_row()` remain
available for inserting explicit values from Python.

To provide individual column values from Python:

```python
tables.insert_random_rows(
    "demo_app", "people", 5, {},
    row_values={"name": ["Alice", "Bob", "Carol", "David", "Eve"]},
)
```

Each `row_values` list or tuple must contain exactly the requested number of
rows. All values are validated against the column type before insertion.

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

## Edit existing row values

Choose **10**, select a database and table, then choose the column to change.
The app displays each existing row and asks for that column's new value.
Leave a value blank to keep the current value for that row. Each entered value
is saved immediately. After going through the rows, choose another column or
leave the column prompt blank to return to the menu. This fills newly added
columns or changes existing values while preserving other columns and the row count.

The table must have a primary key (including composite keys) so each update
identifies a single row. Values are validated against their column types, and
generated columns cannot be edited. Updates require UPDATE permission; server
constraints still apply. Each saved row is committed separately.

```python
tables.update_row("demo_app", "people", {"id": 1}, {"age": 32})
```
