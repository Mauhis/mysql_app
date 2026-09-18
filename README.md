# MySQL Database Creator

An interactive Python command-line application for connecting to an existing
MySQL server, listing visible databases, and creating empty databases.

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
it does not create tables, manage records, run migrations, or delete databases.
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
0. Exit
```

- **1 — List databases:** prints one visible database name per line. Visibility
  depends on the connected account's permissions. An empty result prints
  `No databases visible.`
- **2 — Create database:** asks for a name and creates the database immediately.
  Successful creation prints a confirmation and returns to the menu.
- **0 — Exit:** closes the connection and ends the program.

Other choices print `Choose 1, 2, or 0.` and return to the menu. Operation errors
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
0. Exit
Choose an option: 2
New database name: demo_app
Database 'demo_app' created successfully.

1. List databases
2. Create database
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
produce a server error because the app does not use `IF NOT EXISTS`. No overwrite
or deletion operation is provided. Database name case behavior is determined by
the server; the app preserves the entered case.

## Project layout

```text
mysql_app/
├── ConnManager.py                 # Reusable connection and database operations
├── main.py                        # Interactive prompts, menu, and entry point
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
