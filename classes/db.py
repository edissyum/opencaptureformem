import sqlite3
import sys

class Database:

    def __init__(self, pathToDb):
        try:
            self.conn = sqlite3.connect(pathToDb)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print('Error connecting to database : ' + str(e))

    def create(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS zipCode(
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                zip INTEGER
            )
        """)

        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS cedex(
                    id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    zip INTEGER
                )
            """)

        self.conn.commit()

    def insert(self):
        with open('db/cedex.txt', 'r') as fp:
            line = fp.readline()
            cnt  = 1
            while line:
                self.cursor.execute("INSERT INTO cedex(zip) VALUES(" + line.strip() + ")")
                line = fp.readline()
                cnt += 1
            self.conn.commit()

    def select(self, table, where):
        self.cursor.execute("SELECT * FROM " + table + " WHERE " + where)
        res = self.cursor.fetchone()
        return res
