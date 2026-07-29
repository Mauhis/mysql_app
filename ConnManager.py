from getpass import getpass

import mysql.connector

class ConnectionManager:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host = input("Enter host: "),
                user = input("Enter username: "),
                password = getpass("Enter password: ")
            )
            print("Connection established successfully.")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            self.connection = None