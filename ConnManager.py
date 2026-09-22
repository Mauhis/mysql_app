"""MySQL connection lifecycle and shared SQL execution."""

import mysql.connector


class ConnectionManager:
    """Own a server connection and release cursors after executing SQL."""

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

    def execute(self, statement, *, fetch=False):
        """Execute one statement, always releasing its cursor afterward."""
        cursor = self._cursor()
        try:
            cursor.execute(statement)
            return cursor.fetchall() if fetch else None
        finally:
            cursor.close()

    def close(self):
        """Close and clear the connection; safe to call again after cleanup."""
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                # Clear the reference even if closing raises, so it cannot be reused.
                self.connection = None
