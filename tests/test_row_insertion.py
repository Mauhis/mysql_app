"""Batch insertion and random integer input tests."""
import unittest
from unittest.mock import MagicMock, patch

import mysql.connector

from cli import handle_menu_choice
from ConnManager import ConnectionManager
from table_operations import TableOperations


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.manager = ConnectionManager()
        self.manager.connection = MagicMock()
        self.cursor = self.manager.connection.cursor.return_value
        self.tables = TableOperations(self.manager)

    def test_parameters_column_order_and_single_commit(self):
        self.assertEqual(self.tables.insert_rows('demo', 'staff', [
            {'id': 1, 'name': "O'Reilly"}, {'name': 'Ann', 'id': 2},
        ]), 2)
        self.cursor.execute.assert_called_once_with(
            'INSERT INTO `demo`.`staff` (`id`, `name`) VALUES (%s, %s), (%s, %s)',
            (1, "O'Reilly", 2, 'Ann'))
        self.manager.connection.commit.assert_called_once()

    def test_invalid_batches_do_not_execute(self):
        for rows in ([], [{}], [{'id': 1}, {'name': 'Ann'}], [{'id': 1}, None]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.tables.insert_rows('demo', 'staff', rows)
        self.cursor.execute.assert_not_called()

    def test_failure_rolls_back(self):
        self.cursor.execute.side_effect = mysql.connector.Error('Duplicate ID')
        with self.assertRaises(mysql.connector.Error):
            self.tables.insert_rows('demo', 'staff', [{'id': 1}, {'id': 1}])
        self.manager.connection.rollback.assert_called_once()
        self.manager.connection.commit.assert_not_called()
        self.cursor.close.assert_called_once()


class RandomRowsTests(BatchTests):
    def setUp(self):
        super().setUp()
        self.cursor.fetchall.return_value = [('salary', 'int'), ('offset', 'int'), ('x', 'int')]

    def test_random_ranges_and_count(self):
        with patch('column_values.randint', side_effect=[5000, -2, 10000, 2]) as random:
            count = self.tables.insert_random_rows(
                'demo', 'staff', 2, {'salary': (5000, 10000), 'offset': (-2, 2)})
        self.assertEqual(count, 2)
        self.assertEqual(self.cursor.execute.call_args.args[1], (5000, -2, 10000, 2))
        self.assertEqual(random.call_count, 4)

    def test_equal_bounds(self):
        self.tables.insert_random_rows('demo', 'staff', 10, {'salary': (7, 7)})
        self.assertEqual(self.cursor.execute.call_args.args[1], (7,) * 10)

    def test_invalid_random_parameters(self):
        for count, ranges in ((0, {'x': (1, 2)}), (True, {'x': (1, 2)}),
                              (2, {}), (2, {'x': (2, 1)}),
                              (2, {'x': (1.5, 2)}), (2, {'x': (1,)}),
                              (2, {'bad`column': (1, 2)})):
            with self.subTest(count=count, ranges=ranges), self.assertRaises(ValueError):
                self.tables.insert_random_rows('demo', 'staff', count, ranges)
        self.assertFalse(any(call.args[0].startswith('INSERT')
                             for call in self.cursor.execute.call_args_list))

    def test_list_columns(self):
        self.cursor.fetchall.return_value = [('salary', 'int'), ('age', 'int')]
        self.assertEqual(self.tables.list_columns('demo', 'staff'), ['salary', 'age'])
        self.cursor.execute.assert_called_once_with('SHOW COLUMNS FROM `demo`.`staff`')


class InputTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.list_databases.return_value = ['demo']
        self.tables = MagicMock(spec=TableOperations)
        self.tables.list_tables.return_value = ['staff']
        self.tables.column_types.return_value = {'salary': 'int', 'age': 'int'}

    def run_input(self, answers):
        with patch('builtins.input', side_effect=['demo', 'staff'] + answers), patch('builtins.print'):
            handle_menu_choice(self.db, self.tables, '8')

    def test_salary_only(self):
        self.run_input(['10', 'salary', '', '5000', '10000', ''])
        self.tables.insert_random_rows.assert_called_once_with(
            'demo', 'staff', 10, {'salary': (5000, 10000)})

    def test_multiple_columns(self):
        self.run_input(['10', 'salary', '', '-10', '10', 'age', '', '20', '60', ''])
        self.tables.insert_random_rows.assert_called_once_with(
            'demo', 'staff', 10, {'salary': (-10, 10), 'age': (20, 60)})

    def test_invalid_input_never_inserts(self):
        for answers in (['0'], ['abc'], ['1', 'missing'],
                        ['1', 'salary', '', '10', '5'], ['1', 'salary', '', 'abc'],
                        ['1', 'salary', '', '1', '2', 'salary']):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                self.run_input(answers)
        self.tables.insert_random_rows.assert_not_called()


class TypedRowsTests(unittest.TestCase):
    def test_mixed_column_batch(self):
        from decimal import Decimal
        manager = MagicMock()
        manager.execute.return_value = [
            ('price', 'decimal(8,2)'), ('ratio', 'double'),
            ('label', 'varchar(12)'), ('day', 'date')]
        tables = TableOperations(manager)
        tables.insert_random_rows('demo', 'items', 20,
                                  {'price': ('1.25', '1.30'), 'ratio': (-0.5, 0.5)},
                                  values={'label': "O'Reilly", 'day': '2026-09-30'})
        params = manager.execute.call_args.kwargs['params']
        for index in range(0, len(params), 4):
            self.assertIsInstance(params[index], Decimal)
            self.assertTrue(Decimal('1.25') <= params[index] <= Decimal('1.30'))
            self.assertTrue(-0.5 <= params[index + 1] <= 0.5)
            self.assertEqual(params[index + 2], "O'Reilly")
            self.assertEqual(str(params[index + 3]), '2026-09-30')

    def test_type_limits_and_invalid_values(self):
        from column_values import ColumnValues
        cases = [('int unsigned', '-1'), ('tinyint', '128'), ('int', '1.5'),
                 ('decimal(5,2)', '1000'), ('decimal(5,2)', '1.001'),
                 ('double', 'nan'), ('float', '1e39'), ('double', 'inf'),
                 ('varchar(2)', 'long'), ('date', '2026-02-30')]
        for kind, value in cases:
            with self.subTest(kind=kind, value=value), self.assertRaises(ValueError):
                ColumnValues(kind).parse(value)

    def test_large_decimals_preserve_precision(self):
        from column_values import ColumnValues
        from decimal import Decimal
        value = '123456789012345678901234567890.12'
        generate = ColumnValues('decimal(40,2)').generator((value, value))
        self.assertEqual(generate(), Decimal(value))

    def test_generated_columns_are_excluded(self):
        manager = MagicMock()
        manager.execute.return_value = [
            ('id', 'int', 'NO', 'PRI', None, 'auto_increment'),
            ('total', 'int', 'YES', '', None, 'STORED GENERATED')]
        tables = TableOperations(manager)
        self.assertEqual(tables.column_types('demo', 'items'), {'id': 'int'})
        with self.assertRaises(ValueError):
            tables.insert_random_rows('demo', 'items', 1, {'total': (1, 2)})
        self.assertFalse(any(call.args[0].startswith('INSERT')
                             for call in manager.execute.call_args_list))

    def test_cli_mixed_values(self):
        db = MagicMock()
        db.list_databases.return_value = ['demo']
        tables = MagicMock(spec=TableOperations)
        tables.list_tables.return_value = ['items']
        tables.column_types.return_value = {'price': 'decimal(5,2)', 'name': 'text'}
        answers = ['demo', 'items', '3', 'price', '', '1.25', '2.50', 'name', '', 'Book', '']
        with patch('builtins.input', side_effect=answers), patch('builtins.print'):
            handle_menu_choice(db, tables, '8')
        from decimal import Decimal
        tables.insert_random_rows.assert_called_once_with(
            'demo', 'items', 3, {'price': (Decimal('1.25'), Decimal('2.50'))},
            values={'name': 'Book'})


class ManualRowsTests(unittest.TestCase):
    def test_manual_values_mix_with_ranges_and_fixed_values(self):
        manager = MagicMock()
        manager.execute.return_value = [('name', 'varchar(30)'), ('age', 'int'),
                                        ('label', 'text'), ('score', 'int')]
        tables = TableOperations(manager)
        tables.insert_random_rows('demo', 'staff', 2, {'score': (7, 7)},
                                  values={'label': 'new'},
                                  row_values={'name': ["O'Reilly", ' Ann '],
                                              'age': ['21', '32']})
        self.assertEqual(manager.execute.call_args.kwargs['params'],
                         (7, 'new', "O'Reilly", 21, 7, 'new', ' Ann ', 32))

    def test_invalid_manual_values_never_insert(self):
        for entries in (['Ann'], ['Ann', 'Bob', 'Cat'], 'Ann', ['Ann', 'Too long']):
            with self.subTest(entries=entries):
                manager = MagicMock()
                manager.execute.return_value = [('name', 'varchar(3)')]
                with self.assertRaises(ValueError):
                    TableOperations(manager).insert_random_rows(
                        'demo', 'staff', 2, {}, row_values={'name': entries})
                self.assertFalse(any(call.args[0].startswith('INSERT')
                                     for call in manager.execute.call_args_list))

    def test_duplicate_modes_rejected(self):
        with self.assertRaises(ValueError):
            TableOperations(MagicMock()).insert_random_rows(
                'demo', 'staff', 1, {}, values={'name': 'Ann'},
                row_values={'name': ['Bob']})

    def test_cli_five_names_retries_invalid_value(self):
        db = MagicMock()
        db.list_databases.return_value = ['demo']
        tables = MagicMock(spec=TableOperations)
        tables.list_tables.return_value = ['staff']
        tables.column_types.return_value = {'name': 'varchar(5)'}
        names = ['Alice', 'Bob', 'Carol', 'David', 'Eve']
        answers = ['demo', 'staff', '5', 'name', 'manual', 'Too long', *names, '']
        with patch('builtins.input', side_effect=answers) as prompt, patch('builtins.print'):
            handle_menu_choice(db, tables, '8')
        tables.insert_random_rows.assert_called_once_with(
            'demo', 'staff', 5, {}, values={}, row_values={'name': names})
        self.assertEqual(sum('row 1/5' in call.args[0]
                             for call in prompt.call_args_list), 2)
