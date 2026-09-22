"""Reusable table operations over a shared connection."""

import re

from validation import validate_identifier


class TableOperations:
    """Execute operations using the supplied connection manager."""

    def __init__(self, manager):
        self.manager = manager

    def create_table(self, database, name, columns, primary_key=None):
        """Create a table using a mapping of column names to supported SQL types.

        Types: INT, BIGINT, FLOAT, DOUBLE, BOOLEAN, DATE, DATETIME, TIMESTAMP,
        TEXT, VARCHAR(n), and DECIMAL(p, s). An optional primary_key names one
        column. Server errors (including existing tables) propagate unchanged.
        """
        validate_identifier(database, protect_system=True)
        validate_identifier(name)
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
        if primary_key is not None:
            validate_identifier(primary_key)
            if primary_key not in columns:
                raise ValueError("Primary key must name a defined column exactly.")
            definitions.append(f"PRIMARY KEY (`{primary_key}`)")
        self.manager.execute(
            f"CREATE TABLE `{database}`.`{name}` ({', '.join(definitions)})"
        )
