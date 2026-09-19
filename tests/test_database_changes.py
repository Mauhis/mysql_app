"""Regression checks for destructive operations and their confirmation prompts."""
import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from ConnManager import ConnectionManager
from cli import run_application


class DatabaseChangeTests(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.manager.connection = MagicMock()
        self.cursor = self.manager.connection.cursor.return_value

    def test_delete(self):
        self.manager.delete_database('example')
        self.cursor.execute.assert_called_once_with('DROP DATABASE `example`')
        self.cursor.close.assert_called_once()

    def test_modify(self):
        self.manager.modify_database('example', 'utf8mb4', 'utf8mb4_unicode_ci')
        self.cursor.execute.assert_called_once_with(
            'ALTER DATABASE `example` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
        )
        self.cursor.close.assert_called_once()

    def test_reject_unsafe_names_and_system_databases(self):
        for name in ('', 'bad`name', 'a' * 65, 'mysql', 'MYSQL',
                     'sys', 'information_schema', 'performance_schema'):
            for operation in (self.manager.delete_database,
                              lambda n: self.manager.modify_database(n, 'utf8mb4', 'utf8mb4_bin')):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    operation(name)
        self.manager.connection.cursor.assert_not_called()

    def test_reject_unsafe_options(self):
        for charset, collation in (('', 'utf8mb4_bin'), ('utf8mb4', 'bad; SQL'),
                                    ('utf8mb4; SQL', 'utf8mb4_bin')):
            with self.assertRaises(ValueError):
                self.manager.modify_database('example', charset, collation)
        self.manager.connection.cursor.assert_not_called()

    def test_errors_propagate_and_release_cursor(self):
        for method, args in ((self.manager.delete_database, ('missing',)),
                             (self.manager.modify_database, ('example', 'utf8mb4', 'latin1_bin'))):
            self.cursor.reset_mock()
            self.cursor.execute.side_effect = mysql.connector.Error('Server rejected operation')
            with self.assertRaises(mysql.connector.Error):
                method(*args)
            self.cursor.close.assert_called_once()

    def test_disconnected_changes(self):
        self.manager.connection = None
        for method, args in ((self.manager.delete_database, ('example',)),
                             (self.manager.modify_database, ('example', 'utf8mb4', 'utf8mb4_bin'))):
            with self.assertRaises(RuntimeError):
                method(*args)


class MenuChangeTests(unittest.TestCase):
    def run_menu(self, answers):
        with patch('cli.ConnectionManager') as manager_class, \
                patch('builtins.input', side_effect=['', '', '', *answers]), \
                patch('cli.getpass', return_value='secret'), patch('builtins.print'):
            manager = manager_class.return_value
            manager.list_databases.return_value = ['example']
            self.assertEqual(run_application(), 0)
            manager.close.assert_called_once()
            return manager

    def test_delete_requires_exact_confirmation(self):
        for answer in ('', 'yes', 'DELETE other', 'DELETE example '):
            manager = self.run_menu(['4', 'example', answer, '0'])
            manager.delete_database.assert_not_called()

    def test_confirmed_delete(self):
        manager = self.run_menu(['4', 'example', 'DELETE example', '0'])
        manager.delete_database.assert_called_once_with('example')

    def test_modify_confirmation(self):
        for confirmation in ('', 'MODIFY'):
            manager = self.run_menu(['3', 'example', 'utf8mb4', 'utf8mb4_bin', confirmation, '0'])
            if confirmation:
                manager.modify_database.assert_called_once_with('example', 'utf8mb4', 'utf8mb4_bin')
            else:
                manager.modify_database.assert_not_called()

    def test_missing_database_does_not_mutate(self):
        manager = self.run_menu(['4', 'missing', '0'])
        manager.delete_database.assert_not_called()

    def test_interrupted_confirmation_does_not_delete(self):
        manager = self.run_menu(['4', 'example', KeyboardInterrupt()])
        manager.delete_database.assert_not_called()


if __name__ == '__main__':
    unittest.main()
