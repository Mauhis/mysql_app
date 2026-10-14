"""Read-only table browsing and menu regression tests."""

import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from ConnManager import ConnectionManager
from cli import run_menu
from database_operations import DatabaseOperations
from table_operations import TableOperations


class TableBrowsingTests(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.manager.connection = MagicMock()
        self.cursor = self.manager.connection.cursor.return_value
        self.tables = TableOperations(self.manager)

    def test_list_tables_and_empty_database(self):
        for rows, expected in [([('items',), ('orders',)], ['items', 'orders']), ([], [])]:
            self.cursor.fetchall.return_value = rows
            self.assertEqual(self.tables.list_tables('example'), expected)
        self.cursor.execute.assert_called_with('SHOW TABLES FROM `example`')
        self.assertEqual(self.cursor.close.call_count, 2)
        self.manager.connection.commit.assert_not_called()

    def test_read_values_and_empty_table_preserve_headers(self):
        self.cursor.column_names = ('id', 'value')
        for rows in [[(1, None), (2, "O'Reilly")], []]:
            self.cursor.fetchall.return_value = rows
            self.assertEqual(self.tables.read_table('example', 'items'),
                             (['id', 'value'], rows))
        self.cursor.execute.assert_called_with('SELECT * FROM `example`.`items`')
        self.assertEqual(self.cursor.close.call_count, 2)
        self.manager.connection.commit.assert_not_called()

    def test_invalid_identifiers_do_not_open_cursor(self):
        for database, table in [('bad`db', 'items'), ('example', 'items; DROP TABLE x')]:
            with self.assertRaises(ValueError):
                self.tables.read_table(database, table)
        with self.assertRaises(ValueError):
            self.tables.list_tables('bad`db')
        self.manager.connection.cursor.assert_not_called()

    def test_read_failure_closes_cursor(self):
        self.cursor.execute.side_effect = mysql.connector.Error('Access denied')
        with self.assertRaises(mysql.connector.Error):
            self.tables.read_table('example', 'items')
        self.cursor.close.assert_called_once()

    def run_choices(self, answers, names, result=None, error=None):
        db = MagicMock(spec=DatabaseOperations)
        db.list_databases.return_value = ['example']
        tables = MagicMock(spec=TableOperations)
        tables.list_tables.return_value = names
        tables.read_table.return_value = result
        tables.read_table.side_effect = error
        with patch('builtins.input', side_effect=['2', *answers, '0']), patch('builtins.print') as output:
            run_menu(db, tables)
        return tables, '\n'.join(str(c.args[0]) for c in output.call_args_list)

    def test_menu_lists_tables(self):
        tables, output = self.run_choices(['6', 'example', '0'], ['items', 'orders'])
        tables.list_tables.assert_called_once_with('example')
        self.assertIn('items\norders', output)

    def test_menu_renders_values(self):
        tables, output = self.run_choices(
            ['7', 'example', 'items', '0'], ['items'],
            (['id', 'value'], [(1, None), (2, 'NULL'), (3, 'line\nbreak')]))
        tables.read_table.assert_called_once_with('example', 'items')
        for value in ['id', 'value', 'NULL', "'NULL'", "'line\\nbreak'", '3 row(s).']:
            self.assertIn(value, output)

    def test_empty_table_and_database(self):
        _, output = self.run_choices(['7', 'example', 'items', '0'], ['items'], (['id'], []))
        self.assertIn('id\n--\nTable is empty.', output)
        for choice in ['6', '7']:
            tables, output = self.run_choices([choice, 'example', '0'], [])
            self.assertIn('No tables visible.', output)
            tables.read_table.assert_not_called()

    def test_invalid_selection_and_server_error_return_to_menu(self):
        tables, output = self.run_choices(['7', 'example', 'missing', '0'], ['items'])
        tables.read_table.assert_not_called()
        self.assertIn('Operation failed:', output)
        _, output = self.run_choices(['7', 'example', 'items', '0'], ['items'],
                                     error=mysql.connector.Error('Access denied'))
        self.assertIn('Operation failed: Access denied', output)


if __name__ == '__main__':
    unittest.main()
