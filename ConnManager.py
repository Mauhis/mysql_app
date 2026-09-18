"""Reusable MySQL server connection and database creation operations."""

import re
import mysql.connector


class ConnectionManager:
    """Manage a server connection and database operations."""

    def __init__(self):
        # None means no server connection has been opened yet.
        self.connection = None

    def connect(self, host, user, password, port=3306):
        """Replace the current connection; propagate connector failures to callers."""
        # Release any previous session before opening a replacement.
        self.close()
        # Connect to the server without selecting a database, so we can create one.
        self.connection = mysql.connector.connect(
            host=host, user=user, password=password, port=port,
            connection_timeout=10,
        )

    def _cursor(self):
        """Return a cursor, or raise RuntimeError if there is no live connection."""
        if self.connection is None or not self.connection.is_connected():
            raise RuntimeError("Not connected to a MySQL server.")
        # A cursor sends SQL statements and reads their result rows.
        return self.connection.cursor()

    def list_databases(self):
        """Return visible database names and close the cursor on success or failure."""
        cursor = self._cursor()
        try:
            cursor.execute("SHOW DATABASES")
            # Each result row is a tuple like ('my_database',); take its first value.
            return [row[0] for row in cursor.fetchall()]
        finally:
            # finally runs even if executing SQL or reading the results fails.
            cursor.close()

    def create_database(self, name):
        """Create an empty utf8mb4 database from a restricted ASCII identifier.

        Invalid string names raise ValueError before SQL is sent. Connection and
        server errors propagate; existing databases are never overwritten.
        """
        # SQL parameters cannot represent identifiers. Restrict names before quoting.
        # The pattern requires a letter/underscore, then up to 63 allowed characters.
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name):
            raise ValueError(
                "Use 1–64 letters, digits, or underscores; "
                "start with a letter or underscore."
            )
        cursor = self._cursor()
        try:
            # utf8mb4 supports Unicode; the collation sets text comparison rules.
            # Backticks quote the validated database name as an SQL identifier.
            cursor.execute(
                f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_unicode_ci"
            )
        finally:
            # Release the cursor while keeping the server connection open for reuse.
            cursor.close()

    def close(self):
        """Close and clear the connection; safe to call again after cleanup."""
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                # Clear the reference even if closing raises, so it cannot be reused.
                self.connection = None
