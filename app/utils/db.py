import os
import sqlite3

from sqlite3 import Error
from utils.intra import IntraAPIClient

# outside of class Db because SQLite cursor can't be shared between threads
def populate_users():
  db = Db()
  in_db = db.select('SELECT * FROM users ORDER BY updated_at DESC LIMIT 1')
  if in_db:
      return

  print("Fetching users from intranet")
  ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
  users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users")
  values = [(user['login'], user['image']['link'], user['updated_at']) for user in users]
  db.executemany('INSERT OR IGNORE INTO users (login, link, updated_at) VALUES (?, ?, ?)', values)
  print("Done fetching users from intranet")

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

  def execute(self, sql, values=None):
    if self.conn is None:
      return

    try:
      c = self.conn.cursor()
      if values:
        c.execute(sql, values)
      else:
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
        link TEXT,
        updated_at TEXT
      );
    """)

  def destroy(self):
    self.execute('DROP TABLE users;')


db = Db()