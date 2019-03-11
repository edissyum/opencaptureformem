import sqlite3
import sys

def connect():
    conn = sqlite3.connect('db/zipcode.db')
    return conn

def create(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zipCode(
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            zip INTEGER
        )
    """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS cedex(
                id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                zip INTEGER
            )
        """)

    conn.commit()

def insert(conn):
    cursor = conn.cursor()
    with open('db/cedex.txt', 'r') as fp:
        line = fp.readline()
        cnt  = 1
        while line:
            cursor.execute("INSERT INTO cedex(zip) VALUES(" + line.strip() + ")")
            line = fp.readline()
            cnt += 1
            conn.commit()

def select(conn, table, where):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM " + table + " WHERE " + where)
    res = cursor.fetchone()
    return res

if __name__ == '__main__':
    conn = connect()
    #create(conn)
    #insert(conn)
    #print(select(conn, 84000))