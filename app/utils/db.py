import os
import sqlite3

from sqlite3 import Error
from utils.intra import IntraAPIClient

class Db:
  def __init__(self):
    self.conn = self.create_connection("db.sqlite3")

  def create_connection(self, db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn

  def select(self, query, params=None):
    if self.conn is None:
      return

    cursor = self.conn.cursor()
    if params:
      cursor.execute(query, params)
    else:
      cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in results]

  def execute(self, sql):
    if self.conn is None:
      return

    try:
      c = self.conn.cursor()
      c.execute(sql)
      self.conn.commit()
    except Error as e:
      print(e)

  def executemany(self, sql, values):
    if self.conn is None:
      return

    try:
      c = self.conn.cursor()
      c.executemany(sql, values)
      self.conn.commit()
    except Error as e:
      print(e)

  def create_db(self):
    self.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        login TEXT UNIQUE,
        link TEXT
      );
    """)

  def populate_users(self):
    print("Fetching users from intranet")
    ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
    users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users")
    values = [(user['login'], user['image']['link']) for user in users]
    self.executemany('INSERT OR IGNORE INTO users (login, link) VALUES (?, ?)', values)


db = Db()