"""Small Tkinter desktop client for creating SQL practice datasets."""

from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from ConnManager import ConnectionManager
from column_values import ColumnValues
from database_operations import DatabaseOperations
from table_operations import TableOperations
from validation import validate_identifier


class DesktopApp:
    def __init__(self, root):
        self.root = root
        self.manager = ConnectionManager()
        self.databases = DatabaseOperations(self.manager)
        self.tables = TableOperations(self.manager)
        # All connection access stays on one worker; Tk stays on the main thread.
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.busy = False
        self.closed = False
        self.rows = []
        self.columns = []
        self.types = {}
        self.keys = []
        self.loaded = None
        root.title('MySQL Practice Database Creator')
        root.geometry('1050x650')
        root.minsize(800, 500)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.status = tk.StringVar(value='Connect to your MySQL server to get started.')
        self.connection_frame = ttk.LabelFrame(root, text='MySQL connection', padding=12)
        self.connection_frame.pack(fill='x', padx=16, pady=12)
        self.credentials = {}
        for index, (label, default) in enumerate([
            ('Host', 'localhost'), ('Port', '3306'), ('Username', 'root'), ('Password', '')
        ]):
            ttk.Label(self.connection_frame, text=label).grid(row=0, column=index, sticky='w')
            variable = tk.StringVar(value=default)
            self.credentials[label] = variable
            ttk.Entry(self.connection_frame, textvariable=variable,
                      show='*' if label == 'Password' else '', width=20).grid(
                          row=1, column=index, padx=(0, 10), pady=5)
        ttk.Button(self.connection_frame, text='Connect', command=self.connect).grid(row=1, column=4)

        self.workspace = ttk.Frame(root, padding=(16, 0))
        toolbar = ttk.Frame(self.workspace)
        toolbar.pack(fill='x', pady=(0, 10))
        ttk.Label(toolbar, text='Database').pack(side='left', padx=(0, 8))
        self.database = ttk.Combobox(toolbar, state='readonly', width=28)
        self.database.pack(side='left')
        self.database.bind('<<ComboboxSelected>>', lambda event: self.load_tables())
        ttk.Button(toolbar, text='New database', command=self.create_database).pack(side='left', padx=8)
        ttk.Button(toolbar, text='Refresh', command=self.refresh).pack(side='left')

        body = ttk.Panedwindow(self.workspace, orient='horizontal')
        body.pack(fill='both', expand=True)
        sidebar = ttk.Frame(body, padding=(0, 0, 12, 0))
        body.add(sidebar, weight=1)
        ttk.Label(sidebar, text='Tables').pack(anchor='w')
        self.table_list = tk.Listbox(sidebar, exportselection=False, width=23)
        self.table_list.pack(fill='both', expand=True, pady=8)
        self.table_list.bind('<<ListboxSelect>>', lambda event: self.load_data())
        ttk.Button(sidebar, text='Create table', command=self.create_table).pack(fill='x')
        content = ttk.Frame(body)
        body.add(content, weight=5)
        actions = ttk.Frame(content)
        actions.pack(fill='x', pady=(0, 8))
        for label, callback in [('Add row', lambda: self.row_dialog(False)),
                                ('Edit selected row', lambda: self.row_dialog(True)),
                                ('Add column', self.add_column),
                                ('Delete column', self.delete_column)]:
            ttk.Button(actions, text=label, command=callback).pack(side='left', padx=(0, 8))
        grid = ttk.Frame(content)
        grid.pack(fill='both', expand=True)
        grid.rowconfigure(0, weight=1)
        grid.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(grid, show='headings', selectmode='browse')
        self.tree.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(grid, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(grid, orient='horizontal', command=self.tree.xview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind('<Double-1>', lambda event: self.row_dialog(True))
        ttk.Label(root, textvariable=self.status, padding=12).pack(side='bottom', fill='x')

    def submit(self, operation, success):
        if self.busy or self.closed:
            return
        self.busy = True
        self.status.set('Working…')
        future = self.worker.submit(operation)

        def poll():
            if self.closed:
                return
            if not future.done():
                self.root.after(50, poll)
                return
            self.busy = False
            try:
                result = future.result()
            except Exception as error:
                self.status.set('Operation failed.')
                messagebox.showerror('Operation failed', str(error), parent=self.root)
            else:
                self.status.set('Ready.')
                success(result)
        self.root.after(50, poll)

    def connect(self):
        if self.busy:
            return
        try:
            port = int(self.credentials['Port'].get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror('Invalid port', 'Enter a port between 1 and 65535.')
            return
        details = dict(host=self.credentials['Host'].get().strip(), port=port,
                       user=self.credentials['Username'].get().strip(),
                       password=self.credentials['Password'].get())

        def operation():
            self.manager.connect(**details)
            return self.databases.list_databases()

        def connected(names):
            self.credentials['Password'].set('')
            self.connection_frame.pack_forget()
            self.workspace.pack(fill='both', expand=True)
            self.show_databases(names)
        self.submit(operation, connected)

    def show_databases(self, names, preferred=None):
        self.database['values'] = names
        current = preferred or self.database.get()
        self.database.set(current if current in names else (names[0] if names else ''))
        self.load_tables()

    def refresh(self):
        self.submit(self.databases.list_databases, self.show_databases)

    def clear_data(self):
        self.loaded = None
        self.rows, self.columns, self.types, self.keys = [], [], {}, []
        self.tree.delete(*self.tree.get_children())
        self.tree['columns'] = ()

    def load_tables(self):
        if self.busy:
            return
        self.clear_data()
        self.table_list.delete(0, 'end')
        database = self.database.get()
        if database:
            self.submit(lambda: self.tables.list_tables(database),
                        lambda names: self.table_list.insert('end', *names) if names else None)

    def selected_table(self):
        selection = self.table_list.curselection()
        if not selection:
            raise ValueError('Select a table first.')
        return self.database.get(), self.table_list.get(selection[0])

    def load_data(self):
        if self.busy:
            return
        try:
            database, name = self.selected_table()
        except ValueError:
            return
        self.clear_data()

        def operation():
            return (self.tables.read_table(database, name),
                    self.tables.column_types(database, name),
                    self.tables.primary_key_columns(database, name))

        def display(result):
            if self.database.get() != database:
                self.load_tables()
                return
            if self.selected_table() != (database, name):
                self.load_data()
                return
            (self.columns, self.rows), self.types, self.keys = result
            self.loaded = (database, name)
            # Use numeric widget identifiers so arbitrary SQL column names work.
            identifiers = [str(index) for index in range(len(self.columns))]
            self.tree['columns'] = identifiers
            for identifier, column in zip(identifiers, self.columns):
                self.tree.heading(identifier, text=column)
                self.tree.column(identifier, width=140, minwidth=80)
            for index, row in enumerate(self.rows):
                self.tree.insert('', 'end', iid=str(index), values=[
                    'NULL' if value is None else str(value) for value in row])
            self.status.set(f'{database}.{name} · {len(self.rows)} rows')
        self.submit(operation, display)

    def dialog(self, title, fields, save):
        if self.busy:
            return
        window = tk.Toplevel(self.root)
        window.title(title)
        window.transient(self.root)
        window.grab_set()
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        entries = {}
        for index, (label, default) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=index, column=0, sticky='w', padx=(0, 12), pady=4)
            variable = tk.StringVar(value=default)
            ttk.Entry(frame, textvariable=variable, width=45).grid(row=index, column=1, pady=4)
            entries[label] = variable

        def apply():
            try:
                save({label: value.get() for label, value in entries.items()})
            except (ValueError, TypeError) as error:
                messagebox.showerror('Invalid input', str(error), parent=window)
                return
            window.destroy()
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky='e', pady=(12, 0))
        ttk.Button(buttons, text='Cancel', command=window.destroy).pack(side='left', padx=8)
        ttk.Button(buttons, text='Save', command=apply).pack(side='left')

    def create_database(self):
        def save(values):
            name = values['Database name'].strip()
            validate_identifier(name)

            def operation():
                self.databases.create_database(name)
                return self.databases.list_databases()
            self.submit(operation, lambda names: self.show_databases(names, name))
        self.dialog('Create database', [('Database name', '')], save)

    def create_table(self):
        database = self.database.get()
        if not database:
            messagebox.showinfo('Select database', 'Create or select a database first.')
            return

        def save(values):
            columns = parse_column_definitions(values['Columns (name:type; name:type)'])
            name = values['Table name'].strip()
            key = values['Primary key (optional)'].strip() or None
            validate_identifier(name)
            if key is not None and key not in columns:
                raise ValueError('Primary key must name a defined column exactly.')
            self.submit(lambda: self.tables.create_table(database, name, columns, key),
                        lambda result: self.load_tables())
        self.dialog('Create table', [('Table name', ''),
                    ('Columns (name:type; name:type)', 'id:INT; name:VARCHAR(100)'),
                    ('Primary key (optional)', 'id')], save)

    def add_column(self):
        if not self.loaded or self.busy:
            return
        database, name = self.loaded

        def save(values):
            columns = {values['Column name'].strip(): values['Column type'].strip()}
            self.tables._column_definitions(columns)
            self.submit(lambda: self.tables.add_columns(database, name, columns),
                        lambda result: self.load_data())
        self.dialog('Add column', [('Column name', ''), ('Column type', 'INT')], save)

    def delete_column(self):
        """Remove a selected column after confirming permanent data loss."""
        if not self.loaded or self.busy:
            return
        if len(self.columns) <= 1:
            messagebox.showerror('Cannot delete column', 'At least one column must remain in the table.')
            return
        database, name = self.loaded
        window = tk.Toplevel(self.root)
        window.title('Delete column')
        window.transient(self.root)
        window.grab_set()
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=f'Column to delete from {database}.{name}').pack(anchor='w')
        selection = ttk.Combobox(frame, values=self.columns, state='readonly', width=35)
        selection.pack(fill='x', pady=8)
        selection.current(0)
        ttk.Label(frame, text='Deleting a column permanently removes its stored values.').pack(anchor='w')

        def remove():
            if self.confirm_column_deletion(database, name, selection.get(), window):
                window.destroy()

        buttons = ttk.Frame(frame)
        buttons.pack(anchor='e', pady=(12, 0))
        ttk.Button(buttons, text='Cancel', command=window.destroy).pack(side='left', padx=8)
        ttk.Button(buttons, text='Delete', command=remove).pack(side='left')

    def confirm_column_deletion(self, database, name, column, parent):
        if self.busy:
            return False
        if column not in self.columns or len(self.columns) <= 1:
            raise ValueError('Select an existing column; at least one column must remain.')
        if not messagebox.askyesno(
            'Permanently delete column?',
            f'Delete column "{column}" from {database}.{name}?\n\n'
            'All values in this column will be permanently removed.', parent=parent,
        ):
            return False
        self.submit(lambda: self.tables.drop_columns(database, name, [column]),
                    lambda result: self.load_data())
        return True

    def row_dialog(self, editing):
        if not self.loaded or self.busy:
            return
        database, name = self.loaded
        current = {}
        if editing:
            selection = self.tree.selection()
            if not selection:
                messagebox.showinfo('Select row', 'Select a row in the grid first.')
                return
            if not self.keys:
                messagebox.showerror('Primary key required', 'Editing requires a table with a primary key.')
                return
            current = dict(zip(self.columns, self.rows[int(selection[0])]))
        fields = [(f'{column} ({kind})', '' if current.get(column) is None else str(current[column]))
                  for column, kind in self.types.items()]
        labels = dict(zip(self.types, [label for label, _ in fields]))

        def save(entries):
            values = {}
            for column, label in labels.items():
                raw = entries[label]
                if editing and raw == ('' if current[column] is None else str(current[column])):
                    continue
                if not editing and raw == '':
                    continue
                values[column] = ColumnValues(self.types[column]).parse(raw)
            if not values:
                raise ValueError('Enter at least one new value. Blank fields on new rows use server defaults.')
            operation = (lambda: self.tables.update_row(database, name,
                         {key: current[key] for key in self.keys}, values)) if editing else (
                         lambda: self.tables.insert_row(database, name, values))
            self.submit(operation, lambda result: self.load_data())
        self.dialog('Edit row' if editing else 'Add row (blank fields use defaults)', fields, save)

    def close(self):
        self.closed = True
        self.worker.submit(self.manager.close)
        self.worker.shutdown(wait=False)
        self.root.destroy()


def parse_column_definitions(text):
    """Parse semicolon-separated name:type pairs without splitting DECIMAL commas."""
    columns = {}
    for definition in text.split(';'):
        name, separator, kind = definition.strip().partition(':')
        name, kind = name.strip(), kind.strip()
        if not separator or not name or not kind:
            raise ValueError('Use name:type pairs separated by semicolons.')
        if name.lower() in {column.lower() for column in columns}:
            raise ValueError('Column names must be unique.')
        columns[name] = kind
    TableOperations._column_definitions(columns)
    return columns


def run_desktop():
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()
    return 0
