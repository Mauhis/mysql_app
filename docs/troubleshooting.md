# Troubleshooting

[Back to README](../README.md)

The application includes connector error details after `Connection failed:` or
`Operation failed:`. Use that message to distinguish an unreachable server from
an authentication or permissions problem. Exact wording depends on the server
and connector version.

## Installation and startup

| Symptom | What to check |
| --- | --- |
| `python` is not found | Use `python3` on Linux/macOS or `py -3` on Windows. |
| Virtual environment creation fails | Ensure your Python installation includes `venv`; some OS packages install it separately. |
| `ModuleNotFoundError: No module named 'mysql'` | Install requirements using the same interpreter that runs the app: `python -m pip install -r requirements.txt`. |
| The IDE reports a missing connector | Select this project's `.venv` interpreter in the IDE. |
| `main.py` cannot be opened | Run from the project directory containing `main.py`. |
| Password input warns that echo cannot be disabled | Run in a regular terminal instead of an IDE output pane or redirected input stream. |

Check the interpreter and dependency from the environment you intend to use:

```bash
python --version
python -m pip show mysql-connector-python
```

If you have not activated the environment, substitute `.venv/bin/python` on
Linux/macOS or `.\.venv\Scripts\python.exe` on Windows.

## Connection fails

### Cannot connect, connection refused, or timeout

Confirm that the MySQL server is running and that the host and port refer to it.
For a remote server, check network access, server listening configuration, and
firewall rules with the server administrator. `localhost` refers to the machine
or container where Python is running; a server in another container or machine
may need a different host and an exposed port.

The app makes one connection attempt with a 10-second connection timeout, then
exits on a connector error. Restart after correcting the connection details.

### Access denied while connecting

Check the username and password. MySQL accounts can be restricted by client
host, so an account that works locally on the server may not accept a connection
from your machine. Ask the server administrator to verify account access. The
`root` prompt default does not mean a root account is configured or required.

### Authentication or TLS errors

Use the exact connector message when checking the server's authentication and
transport requirements. The app exposes only host, port, username, and password;
custom certificates and other connector options require a code change. Avoid
removing server security requirements merely to silence a connection error.

## Database operations fail

| Symptom | Explanation and next step |
| --- | --- |
| Name validation error | Use 1–64 ASCII letters, digits, or underscores, beginning with a letter or underscore. |
| Database already exists | Choose a different name, or use option 1 to inspect visible databases. The app does not overwrite existing databases. |
| Access denied when creating | Connecting does not guarantee CREATE permission. Ask the administrator to authorize the intended database. |
| An expected database is absent from the list | Check which server and account you used. The server controls database visibility. |
| `Not connected to a MySQL server.` or a lost connection error | Exit and restart. The app does not reconnect automatically. |
| Character set or collation error | Check whether the target server supports the app's fixed `utf8mb4` / `utf8mb4_unicode_ci` settings. |

If a connection drops during creation, the outcome may be uncertain: the server
may have created the database before the connection was lost. Reconnect and list
databases before trying again.

## Reporting a problem

Include the action you attempted, the full error text with sensitive details
removed, Python and connector versions, and whether the server is local or
remote. Include the server version if available. Do not include passwords or
other credentials. State whether the automated tests pass and whether the issue
occurs against a live server; mocked tests cannot establish server compatibility.
