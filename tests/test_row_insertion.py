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
    def test_random_ranges_and_count(self):
        with patch('table_operations.randint', side_effect=[5000, -2, 10000, 2]) as random:
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
        self.cursor.execute.assert_not_called()

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
        self.tables.list_columns.return_value = ['salary', 'age']

    def run_input(self, answers):
        with patch('builtins.input', side_effect=['demo', 'staff'] + answers), patch('builtins.print'):
            handle_menu_choice(self.db, self.tables, '8')

    def test_salary_only(self):
        self.run_input(['10', 'salary', '5000', '10000', ''])
        self.tables.insert_random_rows.assert_called_once_with(
            'demo', 'staff', 10, {'salary': (5000, 10000)})

    def test_multiple_columns(self):
        self.run_input(['10', 'salary', '-10', '10', 'age', '20', '60', ''])
        self.tables.insert_random_rows.assert_called_once_with(
            'demo', 'staff', 10, {'salary': (-10, 10), 'age': (20, 60)})

    def test_invalid_input_never_inserts(self):
        for answers in (['0'], ['abc'], ['1', 'missing'],
                        ['1', 'salary', '10', '5'], ['1', 'salary', 'abc'],
                        ['1', 'salary', '1', '2', 'salary']):
            with self.subTest(answers=answers), self.assertRaises(ValueError):
                self.run_input(answers)
        self.tables.insert_random_rows.assert_not_called()
