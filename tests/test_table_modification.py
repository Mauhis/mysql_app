"""Column alteration SQL, validation, and interactive workflow tests."""
import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from cli import handle_menu_choice, run_menu
from table_operations import TableOperations


class DropColumnsTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.manager.execute.return_value = [('id',), ('name',), ('age',)]
        self.tables = TableOperations(self.manager)

    def test_drop_multiple_columns(self):
        self.tables.drop_columns('demo', 'people', ['name', 'age'])
        self.assertEqual(self.manager.execute.call_args.args,
                         ('ALTER TABLE `demo`.`people` DROP COLUMN `name`, DROP COLUMN `age`',))

    def test_invalid_arguments_never_execute(self):
        for database, name, columns in [
            ('sys', 'people', ['name']), ('bad`db', 'people', ['name']),
            ('demo', 'bad`table', ['name']), ('demo', 'people', []),
            ('demo', 'people', 'name'), ('demo', 'people', ['name', 'NAME']),
            ('demo', 'people', ['bad`column']), ('demo', 'people', [None]),
        ]:
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                self.tables.drop_columns(database, name, columns)
        self.manager.execute.assert_not_called()

    def test_unknown_and_all_columns_never_alter(self):
        for columns in [['missing'], ['id', 'name', 'age']]:
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                self.tables.drop_columns('demo', 'people', columns)
        self.assertTrue(all(call.args[0].startswith('SHOW')
                            for call in self.manager.execute.call_args_list))

    def test_server_error_propagates(self):
        self.manager.execute.side_effect = [[('id',), ('name',)],
                                           mysql.connector.Error('Column dependency')]
        with self.assertRaises(mysql.connector.Error):
            self.tables.drop_columns('demo', 'people', ['name'])


class ModifyTableInputTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.list_databases.return_value = ['demo']
        self.tables = MagicMock(spec=TableOperations)
        self.tables.list_tables.return_value = ['people']
        self.tables.list_columns.return_value = ['id', 'name', 'age']

    def run_input(self, answers):
        with patch('builtins.input', side_effect=['demo', 'people', *answers]), \
                patch('builtins.print'):
            handle_menu_choice(self.db, self.tables, '9')

    def test_add_columns(self):
        self.run_input(['add', 'email', 'VARCHAR(100)', 'score', 'INT', ''])
        self.tables.add_columns.assert_called_once_with(
            'demo', 'people', {'email': 'VARCHAR(100)', 'score': 'INT'})
        self.tables.drop_columns.assert_not_called()

    def test_remove_columns(self):
        self.run_input(['remove', 'name', 'age', '', 'REMOVE'])
        self.tables.drop_columns.assert_called_once_with('demo', 'people', ['name', 'age'])
        self.tables.add_columns.assert_not_called()

    def test_cancel(self):
        for answers in [[''], ['add', ''], ['remove', ''],
                        ['remove', 'name', '', 'no']]:
            self.run_input(answers)
        self.tables.add_columns.assert_not_called()
        self.tables.drop_columns.assert_not_called()

    def test_invalid_selection(self):
        for answers in [['rename'], ['add', 'NAME'], ['remove', 'missing'],
                        ['add', 'email', 'TEXT', 'EMAIL'],
                        ['remove', 'name', 'name'], ['remove', 'id', 'name', 'age', '']]:
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                self.run_input(answers)
        self.tables.add_columns.assert_not_called()
        self.tables.drop_columns.assert_not_called()

    def test_no_tables(self):
        self.tables.list_tables.return_value = []
        with patch('builtins.input', side_effect=['demo']), patch('builtins.print'):
            handle_menu_choice(self.db, self.tables, '9')
        self.tables.list_columns.assert_not_called()

    def test_unknown_table(self):
        with patch('builtins.input', side_effect=['demo', 'missing']), \
                patch('builtins.print'), self.assertRaises(ValueError):
            handle_menu_choice(self.db, self.tables, '9')
        self.tables.list_columns.assert_not_called()

    def test_menu_recovers_from_alter_error(self):
        self.tables.add_columns.side_effect = mysql.connector.Error('ALTER denied')
        with patch('builtins.input', side_effect=[
            '2', '9', 'demo', 'people', 'add', 'email', 'TEXT', '', '0', '0'
        ]), patch('builtins.print') as output:
            run_menu(self.db, self.tables)
        output.assert_any_call('Operation failed: ALTER denied')
