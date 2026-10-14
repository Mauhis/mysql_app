"""Desktop input parsing and background-operation error handling."""
import unittest
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from desktop import DesktopApp, parse_column_definitions


class DesktopTests(unittest.TestCase):
    def test_column_definitions_preserve_decimal_precision(self):
        self.assertEqual(parse_column_definitions('id: INT; price: DECIMAL(10, 2)'),
                         {'id': 'INT', 'price': 'DECIMAL(10, 2)'})

    def test_invalid_column_definitions(self):
        for text in ('', 'id INT', 'id:INT; ID:TEXT', 'id:invalid', 'bad`name:INT'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_column_definitions(text)

    def app_without_window(self):
        app = DesktopApp.__new__(DesktopApp)
        app.root = MagicMock()
        app.worker = MagicMock()
        app.status = MagicMock()
        app.busy = app.closed = False
        return app

    def test_background_failure_allows_retry(self):
        app = self.app_without_window()
        future = Future()
        future.set_exception(ValueError('Invalid data'))
        app.worker.submit.return_value = future
        success = MagicMock()
        app.submit(lambda: None, success)
        poll = app.root.after.call_args.args[1]
        with patch('desktop.messagebox.showerror') as error:
            poll()
        error.assert_called_once()
        success.assert_not_called()
        self.assertFalse(app.busy)

    def test_success_callback_runs_from_tk_poll(self):
        app = self.app_without_window()
        future = Future()
        future.set_result(['demo'])
        app.worker.submit.return_value = future
        success = MagicMock()
        app.submit(lambda: None, success)
        success.assert_not_called()
        app.root.after.call_args.args[1]()
        success.assert_called_once_with(['demo'])

    def test_busy_app_does_not_queue_duplicate_writes(self):
        app = self.app_without_window()
        app.busy = True
        app.submit(lambda: None, MagicMock())
        app.worker.submit.assert_not_called()

    def test_column_deletion_requires_confirmation_and_refreshes(self):
        app = self.app_without_window()
        app.columns = ['id', 'age']
        app.tables = MagicMock()
        app.submit = MagicMock()
        app.load_data = MagicMock()
        with patch('desktop.messagebox.askyesno', return_value=True):
            self.assertTrue(app.confirm_column_deletion('demo', 'people', 'age', None))
        operation, success = app.submit.call_args.args
        operation()
        app.tables.drop_columns.assert_called_once_with('demo', 'people', ['age'])
        success(None)
        app.load_data.assert_called_once()

    def test_cancel_column_deletion_never_submits(self):
        app = self.app_without_window()
        app.columns = ['id', 'age']
        app.submit = MagicMock()
        with patch('desktop.messagebox.askyesno', return_value=False):
            self.assertFalse(app.confirm_column_deletion('demo', 'people', 'age', None))
        app.submit.assert_not_called()

    def test_last_or_unknown_column_never_submits(self):
        app = self.app_without_window()
        app.submit = MagicMock()
        for columns, selected in [(['id'], 'id'), (['id', 'age'], 'missing')]:
            app.columns = columns
            with self.assertRaises(ValueError):
                app.confirm_column_deletion('demo', 'people', selected, None)
        app.submit.assert_not_called()
