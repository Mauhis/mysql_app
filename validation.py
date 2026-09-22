"""Shared validation for SQL identifiers and database options."""

import re


def validate_identifier(name, protect_system=False):
    """Validate an identifier and optionally reject MySQL's system databases."""
    # SQL parameters cannot represent identifiers. Restrict names before quoting.
    # The pattern requires a letter/underscore, then up to 63 allowed characters.
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]{0,63}", name
    ):
        raise ValueError(
            "Use 1–64 letters, digits, or underscores; "
            "start with a letter or underscore."
        )
    if protect_system and name.lower() in {
        "mysql", "information_schema", "performance_schema", "sys"
    }:
        raise ValueError(
            "System databases cannot be modified or deleted by this app."
        )


def validate_sql_name(value, label):
    """Validate a character-set or collation token used in generated SQL."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]{0,63}", value
    ):
        raise ValueError(
            f"{label} must be 1–64 ASCII letters, digits, or underscores, "
            "starting with a letter."
        )
