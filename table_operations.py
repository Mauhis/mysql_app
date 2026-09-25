"""Reusable table operations over a shared connection."""

import re
from random import randint

from validation import validate_identifier


class TableOperations:
    """Execute operations using the supplied connection manager."""

    def __init__(self, manager):
        self.manager = manager

    def list_tables(self, database):
        """Return visible table and view names in a database."""
        validate_identifier(database)
        rows = self.manager.execute(f"SHOW TABLES FROM `{database}`", fetch=True)
        return [row[0] for row in rows]

    def list_columns(self, database, name):
        """Return existing column names without loading table contents."""
        validate_identifier(database)
        validate_identifier(name)
        rows = self.manager.execute(
            f"SHOW COLUMNS FROM `{database}`.`{name}`", fetch=True,
        )
        return [row[0] for row in rows]

    def insert_random_rows(self, database, name, count, ranges):
        """Insert count rows using {column: (minimum, maximum)} integer ranges.

        Both endpoints are inclusive; repeated values are possible. Omitted
        columns use database defaults. The server checks types and constraints.
        """
        validate_identifier(database, protect_system=True)
        validate_identifier(name)
        if type(count) is not int or count <= 0:
            raise ValueError("Number of rows must be a positive integer.")
        if not isinstance(ranges, dict) or not ranges:
            raise ValueError("Select at least one column and its integer range.")
        seen = set()
        for column, bounds in ranges.items():
            validate_identifier(column)
            if column.lower() in seen:
                raise ValueError("Column names must be unique regardless of case.")
            seen.add(column.lower())
            if (not isinstance(bounds, (tuple, list)) or len(bounds) != 2
                    or any(type(value) is not int for value in bounds)
                    or bounds[0] > bounds[1]):
                raise ValueError("Each range needs integer bounds with minimum <= maximum.")
        return self.insert_rows(database, name, [
            {column: randint(*bounds) for column, bounds in ranges.items()}
            for _ in range(count)
        ])

    def read_table(self, database, name):
        """Return (column names, all rows), preserving native values and NULLs."""
        validate_identifier(database)
        validate_identifier(name)
        return self.manager.execute(
            f"SELECT * FROM `{database}`.`{name}`", include_columns=True,
        )

    def create_table(self, database, name, columns, primary_key=None):
        """Create a table using a mapping of column names to supported SQL types.

        Types: INT, BIGINT, FLOAT, DOUBLE, BOOLEAN, DATE, DATETIME, TIMESTAMP,
        TEXT, VARCHAR(n), and DECIMAL(p, s). An optional primary_key names one
        column. Server errors (including existing tables) propagate unchanged.
        """
        validate_identifier(database, protect_system=True)
        validate_identifier(name)
        definitions = self._column_definitions(columns)
        if primary_key is not None:
            validate_identifier(primary_key)
            if primary_key not in columns:
                raise ValueError("Primary key must name a defined column exactly.")
            definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        self.manager.execute(
            f"CREATE TABLE `{database}`.`{name}` ({', '.join(definitions)})"
        )

    @staticmethod
    def _column_definitions(columns):
        """Validate column definitions shared by CREATE and ALTER TABLE."""
        if not isinstance(columns, dict) or not columns:
            raise ValueError("Provide a nonempty dictionary of column names and types.")
        definitions = []
        seen = set()
        for column, data_type in columns.items():
            validate_identifier(column)
            if column.lower() in seen:
                raise ValueError("Column names must be unique regardless of case.")
            seen.add(column.lower())
            if not isinstance(data_type, str):
                raise ValueError("Column types must be strings.")
            data_type = data_type.strip().upper()
            simple = data_type in {
                "INT", "BIGINT", "FLOAT", "DOUBLE", "BOOLEAN", "DATE",
                "DATETIME", "TIMESTAMP", "TEXT",
            }
            varchar = re.fullmatch(r"VARCHAR\(([0-9]{1,5})\)", data_type)
            decimal = re.fullmatch(r"DECIMAL\(([0-9]{1,2}),\s*([0-9]{1,2})\)", data_type)
            if not (
                simple
                or (varchar and 1 <= int(varchar[1]) <= 65535)
                or (decimal and 1 <= int(decimal[1]) <= 65
                    and 0 <= int(decimal[2]) <= min(30, int(decimal[1])))
            ):
                raise ValueError(f"Unsupported or invalid column type: {data_type}")
            definitions.append(f"`{column}` {data_type}")
        return definitions

    def add_columns(self, database, name, columns):
        """Add columns using the same name/type mapping as create_table.

        Existing columns and incompatible definitions produce server errors.
        This schema change takes effect immediately.
        """
        validate_identifier(database, protect_system=True)
        validate_identifier(name)
        definitions = self._column_definitions(columns)
        additions = ", ".join(f"ADD COLUMN {definition}" for definition in definitions)
        self.manager.execute(f"ALTER TABLE `{database}`.`{name}` {additions}")

    def insert_row(self, database, name, values):
        """Insert and commit one row from a nonempty column/value dictionary.

        Values are passed as SQL parameters; None represents SQL NULL.
        Omitted columns use server defaults. The server validates value types
        and constraints. Success returns None; connector errors propagate.
        """
        self.insert_rows(database, name, [values])

    def insert_rows(self, database, name, rows):
        """Insert dictionaries with identical columns and commit once.

        Values are parameterized. Failures roll back on transactional tables.
        Return the inserted count; validate all rows before executing SQL.
        """
        rows = list(rows)
        if not rows:
            raise ValueError("Provide at least one row.")
        values = rows[0]
        validate_identifier(database, protect_system=True)
        validate_identifier(name)
        if not isinstance(values, dict) or not values:
            raise ValueError("Provide a nonempty dictionary of column names and values.")
        seen = set()
        for column in values:
            validate_identifier(column)
            if column.lower() in seen:
                raise ValueError("Column names must be unique regardless of case.")
            seen.add(column.lower())
        columns = ", ".join(f"`{column}`" for column in values)
        placeholders = ", ".join("%s" for _ in values)
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(values):
                raise ValueError("Every row must contain the same column names.")
        groups = ", ".join(f"({placeholders})" for _ in rows)
        self.manager.execute(
            f"INSERT INTO `{database}`.`{name}` ({columns}) VALUES {groups}",
            params=tuple(row[column] for row in rows for column in values),
            commit=True,
        )
        return len(rows)
