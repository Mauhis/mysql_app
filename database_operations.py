"""Reusable database operations over a shared connection."""

from validation import validate_identifier, validate_sql_name


class DatabaseOperations:
    """Execute operations using the supplied connection manager."""

    def __init__(self, manager):
        self.manager = manager

    def list_databases(self):
        """Return visible database names and close the cursor on success or failure."""
        rows = self.manager.execute("SHOW DATABASES", fetch=True)
        # Each result row is a tuple like ('my_database',); take its first value.
        return [row[0] for row in rows]

    def create_database(self, name):
        """Create an empty utf8mb4 database from a restricted ASCII identifier.

        Invalid string names raise ValueError before SQL is sent. Connection and
        server errors propagate; existing databases are never overwritten.
        """
        validate_identifier(name)
        # Backticks quote the validated database name as an SQL identifier.
        self.manager.execute(
            f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )

    def delete_database(self, name):
        """Permanently drop a database. Callers are responsible for confirmation."""
        validate_identifier(name, protect_system=True)
        # No IF EXISTS: a missing database should report an error to the caller.
        self.manager.execute(f"DROP DATABASE `{name}`")

    def modify_database(self, name, charset, collation):
        """Change database defaults without converting existing tables or data."""
        validate_identifier(name, protect_system=True)
        # These SQL tokens are also interpolated, so reject punctuation and spaces.
        for label, value in (("Character set", charset), ("Collation", collation)):
            validate_sql_name(value, label)
        # MySQL validates that the names exist and the collation matches the charset.
        self.manager.execute(
            f"ALTER DATABASE `{name}` CHARACTER SET {charset} COLLATE {collation}"
        )
