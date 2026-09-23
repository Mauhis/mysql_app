"""Table creation validation, connection cleanup, and CLI regression tests."""

import unittest
from unittest.mock import MagicMock, call, patch

import mysql.connector

from ConnManager import ConnectionManager
from database_operations import DatabaseOperations
from table_operations import TableOperations
from cli import run_menu


class TableCreationTests(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.databases = DatabaseOperations(self.manager)
        self.tables = TableOperations(self.manager)
        self.manager.connection = MagicMock()
        self.cursor = self.manager.connection.cursor.return_value

    def test_create_table(self):
        self.tables.create_table(
            "example", "products",
            {"id": "int", "name": "VARCHAR(100)", "price": "DECIMAL(10, 2)"},
            primary_key="id",
        )
        self.cursor.execute.assert_called_once_with(
            "CREATE TABLE `example`.`products` (`id` INT, `name` VARCHAR(100), "
            "`price` DECIMAL(10, 2), PRIMARY KEY (`id`))"
        )
        self.cursor.close.assert_called_once()

    def test_without_primary_key(self):
        self.tables.create_table("example", "events", {"message": "TEXT"})
        self.cursor.execute.assert_called_once_with(
            "CREATE TABLE `example`.`events` (`message` TEXT)"
        )

    def test_invalid_schema_never_opens_cursor(self):
        cases = [
            ("mysql", "items", {"id": "INT"}, None),
            ("bad`db", "items", {"id": "INT"}, None),
            ("example", "bad`table", {"id": "INT"}, None),
            ("example", "items", {}, None),
            ("example", "items", [("id", "INT")], None),
            ("example", "items", {"bad`column": "INT"}, None),
            ("example", "items", {"id": "INT", "ID": "INT"}, None),
            ("example", "items", {"id": "INT"}, "missing"),
        ]
        for data_type in (None, "", "INT); DROP DATABASE example; --",
                          "VARCHAR(0)", "VARCHAR(65536)", "DECIMAL(66,0)",
                          "DECIMAL(10,11)", "DECIMAL(40,31)"):
            cases.append(("example", "items", {"id": data_type}, None))
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                self.tables.create_table(*args)
        self.manager.connection.cursor.assert_not_called()

    def test_server_error_closes_cursor(self):
        self.cursor.execute.side_effect = mysql.connector.Error("Table already exists")
        with self.assertRaises(mysql.connector.Error):
            self.tables.create_table("example", "items", {"id": "INT"})
        self.cursor.close.assert_called_once()

    def test_disconnected(self):
        for connection in (None, MagicMock()):
            if connection is not None:
                connection.is_connected.return_value = False
            self.manager.connection = connection
            with self.assertRaises(RuntimeError):
                self.tables.create_table("example", "items", {"id": "INT"})

    def test_add_columns(self):
        self.tables.add_columns("example", "items", {"label": "varchar(80)", "qty": "INT"})
        self.cursor.execute.assert_called_once_with(
            "ALTER TABLE `example`.`items` ADD COLUMN `label` VARCHAR(80), ADD COLUMN `qty` INT"
        )
        self.cursor.close.assert_called_once()

    def test_insert_row_parameters_and_commit(self):
        value = "O'Reilly'); DROP TABLE items; --"
        self.tables.insert_row("example", "items", {"label": value, "qty": None})
        self.cursor.execute.assert_called_once_with(
            "INSERT INTO `example`.`items` (`label`, `qty`) VALUES (%s, %s)",
            (value, None),
        )
        self.manager.connection.commit.assert_called_once()
        self.cursor.close.assert_called_once()

    def test_invalid_additions_and_rows_do_not_execute(self):
        for method in (self.tables.add_columns, self.tables.insert_row):
            for database, name, mapping in (
                ("sys", "items", {"id": "INT"}),
                ("bad`db", "items", {"id": "INT"}),
                ("example", "bad`table", {"id": "INT"}),
                ("example", "items", {}),
                ("example", "items", [("id", "INT")]),
                ("example", "items", {"bad`column": "INT"}),
                ("example", "items", {"id": "INT", "ID": "INT"}),
            ):
                with self.subTest(method=method.__name__, mapping=mapping):
                    with self.assertRaises(ValueError):
                        method(database, name, mapping)
        with self.assertRaises(ValueError):
            self.tables.add_columns("example", "items", {"id": "INT; DROP TABLE items"})
        self.manager.connection.cursor.assert_not_called()

    def test_insert_failure_rolls_back_and_closes_cursor(self):
        self.cursor.execute.side_effect = mysql.connector.Error("Invalid value")
        with self.assertRaises(mysql.connector.Error):
            self.tables.insert_row("example", "items", {"id": 1})
        self.manager.connection.commit.assert_not_called()
        self.manager.connection.rollback.assert_called_once()
        self.cursor.close.assert_called_once()

    def test_commit_failure_rolls_back_and_closes_cursor(self):
        self.manager.connection.commit.side_effect = mysql.connector.Error("Commit failed")
        with self.assertRaises(mysql.connector.Error):
            self.tables.insert_row("example", "items", {"id": 1})
        self.manager.connection.rollback.assert_called_once()
        self.cursor.close.assert_called_once()

    def test_new_operations_disconnected(self):
        self.manager.connection = None
        for method in (self.tables.add_columns, self.tables.insert_row):
            with self.assertRaises(RuntimeError):
                method("example", "items", {"id": "INT"})

    def test_menu_creates_table(self):
        databases = MagicMock(spec=DatabaseOperations)
        tables = MagicMock(spec=TableOperations)
        databases.list_databases.return_value = ["example"]
        answers = ["5", "example", "items", "id", "INT", "", "id", "0"]
        with patch("builtins.input", side_effect=answers), patch("builtins.print"):
            run_menu(databases, tables)
        tables.create_table.assert_called_once_with(
            "example", "items", {"id": "INT"}, primary_key="id"
        )

    def test_menu_recovers_from_server_error(self):
        self.cursor.execute.side_effect = mysql.connector.Error("Table already exists")
        with patch.object(self.databases, "list_databases", return_value=["example"]), \
                patch("builtins.input", side_effect=[
                    "5", "example", "items", "id", "INT", "", "", "0"
                ]), patch("builtins.print") as output:
            run_menu(self.databases, self.tables)
        output.assert_any_call("Operation failed: Table already exists")

    def test_operations_share_connection_and_observe_close(self):
        self.databases.create_database("example")
        self.tables.create_table("example", "items", {"id": "INT"})
        self.assertEqual(self.cursor.execute.call_args_list, [
            call("CREATE DATABASE `example` CHARACTER SET utf8mb4 "
                 "COLLATE utf8mb4_unicode_ci"),
            call("CREATE TABLE `example`.`items` (`id` INT)"),
        ])
        self.manager.connection.close.assert_not_called()
        self.manager.close()
        with self.assertRaises(RuntimeError):
            self.databases.list_databases()
        with self.assertRaises(RuntimeError):
            self.tables.create_table("example", "items", {"id": "INT"})


if __name__ == "__main__":
    unittest.main()
