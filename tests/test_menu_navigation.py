"""Section navigation and action isolation."""
import unittest
from unittest.mock import MagicMock, patch

from cli import run_menu


class MenuNavigationTests(unittest.TestCase):
    def test_switch_sections_and_exit(self):
        db, tables = MagicMock(), MagicMock()
        with patch('builtins.input', side_effect=[
            '1', '1', '0', '2', '6', 'demo', '0', '0'
        ]), patch('builtins.print'):
            db.list_databases.return_value = ['demo']
            tables.list_tables.return_value = ['people']
            run_menu(db, tables)
        self.assertEqual(db.list_databases.call_count, 2)
        tables.list_tables.assert_called_once_with('demo')

    def test_actions_only_run_in_their_section(self):
        with patch('builtins.input', side_effect=[
            '9', '1', '6', '0', '2', '1', '0', '0'
        ]), patch('builtins.print'), patch('cli.handle_menu_choice') as action:
            run_menu(MagicMock(), MagicMock())
        action.assert_not_called()
