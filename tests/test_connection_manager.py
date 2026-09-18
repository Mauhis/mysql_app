import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from ConnManager import ConnectionManager


class ConnectionManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.connection = MagicMock()
        self.manager.connection = self.connection
        self.cursor = self.connection.cursor.return_value

    def test_create_database(self):
        self.manager.create_database("example_db")
        self.cursor.execute.assert_called_once_with(
            "CREATE DATABASE `example_db` CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )
        self.cursor.close.assert_called_once()

    def test_rejects_invalid_names_before_sql(self):
        for name in ("", "1db", "a b", "a-b", "é", "a" * 65, "x`; DROP DATABASE x;--"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.manager.create_database(name)
        self.connection.cursor.assert_not_called()

    def test_lists_databases(self):
        self.cursor.fetchall.return_value = [("first",), ("second",)]
        self.assertEqual(self.manager.list_databases(), ["first", "second"])
        self.cursor.close.assert_called_once()

    def test_database_error_propagates_and_closes_cursor(self):
        self.cursor.execute.side_effect = mysql.connector.Error("Access denied")
        with self.assertRaises(mysql.connector.Error):
            self.manager.create_database("example")
        self.cursor.close.assert_called_once()

    def test_disconnected_operations(self):
        self.connection.is_connected.return_value = False
        with self.assertRaises(RuntimeError):
            self.manager.list_databases()

    def test_close_is_repeatable(self):
        self.manager.close()
        self.manager.close()
        self.connection.close.assert_called_once()
        self.assertIsNone(self.manager.connection)

    @patch("ConnManager.mysql.connector.connect")
    def test_failed_reconnect_clears_old_connection(self, connect):
        connect.side_effect = mysql.connector.Error("Unavailable")
        with self.assertRaises(mysql.connector.Error):
            self.manager.connect("localhost", "user", "password")
        self.connection.close.assert_called_once()
        self.assertIsNone(self.manager.connection)


if __name__ == "__main__":
    unittest.main()
