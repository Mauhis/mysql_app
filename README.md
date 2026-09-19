# MySQL Database Creator

An interactive Python command-line application for connecting to an existing
MySQL server, listing visible databases, creating empty databases, changing database defaults,
and deleting databases.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Database names and creation behavior](#database-names-and-creation-behavior)
- [Troubleshooting](docs/troubleshooting.md)
- [Developer guide and API reference](docs/development.md)
- [Project layout](#project-layout)
- [License](#license)

## Requirements

- Python 3.10 or newer, with `pip` and virtual environment support.
- An existing, running MySQL server reachable from your machine.
- A MySQL account authorized to connect from your machine and create the intended
  databases. Ask your database administrator for an appropriate account.
- The `mysql-connector-python` dependency declared in `requirements.txt`.

The application does not install or start MySQL. It creates empty databases;
it does not create tables, manage records, run migrations, or rename databases.
There is no graphical interface or web server.

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

## Usage

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

```text
1. List databases
2. Create database
3. Modify database defaults
4. Delete database
0. Exit
```

- **1 — List databases:** prints one visible database name per line. Visibility
  depends on the connected account's permissions. An empty result prints
  `No databases visible.`
- **2 — Create database:** asks for a name and creates the database immediately.
  Successful creation prints a confirmation and returns to the menu.
- **0 — Exit:** closes the connection and ends the program.

Other choices print `Choose 1, 2, 3, 4, or 0.` and return to the menu. Operation errors
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

1. List databases
2. Create database
3. Modify database defaults
4. Delete database
0. Exit
Choose an option: 2
New database name: demo_app
Database 'demo_app' created successfully.

1. List databases
2. Create database
3. Modify database defaults
4. Delete database
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

## Project layout

```text
mysql_app/
├── ConnManager.py                 # Reusable connection and database operations
├── cli.py                         # Interactive prompts and menu workflow
├── main.py                        # Minimal executable entry point
├── requirements.txt               # MySQL connector dependency range
├── tests/test_connection_manager.py
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
