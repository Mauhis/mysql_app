"""Existing rows are updated by primary key without inserting new records."""
import unittest
from unittest.mock import MagicMock, patch, call

from cli import handle_menu_choice
from table_operations import TableOperations


class RowUpdateTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.tables = TableOperations(self.manager)
        self.metadata = [
            ('id', 'int', 'NO', 'PRI', None, ''),
            ('age', 'int', 'YES', '', None, ''),
        ]
        self.manager.execute.return_value = self.metadata

    def test_fill_added_column_preserves_existing_row(self):
        self.tables.update_row('demo', 'people', {'id': 7}, {'age': '32'})
        self.manager.execute.assert_called_with(
            'UPDATE `demo`.`people` SET `age` = %s WHERE `id` = %s',
            params=(32, 7), commit=True)

    def test_composite_key_and_parameterized_text(self):
        self.metadata.append(('name', 'varchar(100)', 'NO', 'PRI', None, ''))
        self.tables.update_row('demo', 'people', {'name': "O'Brien", 'id': 7},
                               {'name': 'Alice', 'age': 23})
        self.manager.execute.assert_called_with(
            'UPDATE `demo`.`people` SET `name` = %s, `age` = %s '
            'WHERE `id` = %s AND `name` = %s',
            params=('Alice', 23, 7, "O'Brien"), commit=True)

    def test_invalid_updates_never_write(self):
        for keys, values in [({}, {'age': 3}), ({'missing': 1}, {'age': 3}),
                             ({'id': None}, {'age': 3}), ({'id': 1}, {}),
                             ({'id': 1}, {'missing': 3}),
                             ({'id': 1}, {'age': 'invalid'})]:
            with self.subTest(keys=keys, values=values), self.assertRaises(ValueError):
                self.tables.update_row('demo', 'people', keys, values)
        self.assertFalse(any(call.kwargs.get('commit')
                             for call in self.manager.execute.call_args_list))

    def test_no_primary_key_never_writes(self):
        self.metadata[0] = ('id', 'int', 'YES', '', None, '')
        with self.assertRaises(ValueError):
            self.tables.update_row('demo', 'people', {'id': 7}, {'age': 32})
        self.manager.execute.assert_called_once()

    def test_cli_selects_column_and_retries_invalid_value(self):
        db = MagicMock()
        db.list_databases.return_value = ['demo']
        tables = MagicMock(spec=TableOperations)
        tables.list_tables.return_value = ['people']
        tables.primary_key_columns.return_value = ['id']
        tables.column_types.return_value = {'id': 'int', 'age': 'int'}
        tables.read_table.return_value = (['id', 'age'], [(7, None), (8, None)])
        with patch('builtins.input', side_effect=[
            'demo', 'people', 'missing', 'age', 'invalid', '32', '45', ''
        ]), patch('builtins.print'):
            handle_menu_choice(db, tables, '10')
        self.assertEqual(tables.update_row.call_args_list, [
            call('demo', 'people', {'id': 7}, {'age': 32}),
            call('demo', 'people', {'id': 8}, {'age': 45}),
        ])
        tables.insert_random_rows.assert_not_called()

    def test_cli_blank_values_preserve_rows(self):
        db = MagicMock()
        db.list_databases.return_value = ['demo']
        tables = MagicMock(spec=TableOperations)
        tables.list_tables.return_value = ['people']
        tables.primary_key_columns.return_value = ['id']
        tables.column_types.return_value = {'id': 'int', 'age': 'int'}
        tables.read_table.return_value = (['id', 'age'], [(7, 20), (8, 30)])
        with patch('builtins.input', side_effect=[
            'demo', 'people', 'age', '', '45', ''
        ]), patch('builtins.print'):
            handle_menu_choice(db, tables, '10')
        tables.update_row.assert_called_once_with('demo', 'people', {'id': 8}, {'age': 45})


if __name__ == '__main__':
    unittest.main()
