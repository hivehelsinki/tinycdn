import os
import sqlite3
import logging
import threading
import requests
from pathlib import Path

from sqlite3 import Error
from utils.intra import IntraAPIClient
from utils.images import download_image
from utils.storage import DATA_DIR, IMAGE_DIR, DATABASE_PATH

LOG = logging.getLogger(__name__)
sync_lock = threading.Lock()
image_lock = threading.RLock()


def remove_image(filename):
  if filename:
    try:
      (IMAGE_DIR / filename).unlink(missing_ok=True)
    except OSError:
      LOG.warning('Could not remove cached image %s', filename)


# Each background thread owns its SQLite connection.
def populate_users(reset=False):
  with sync_lock, Db() as database:
    ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
    if reset:
      # Fetch before clearing the cache, so API errors leave existing data intact.
      users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users", timeout=30)
      with image_lock:
        database.destroy()
        database.create_db()
        for path in IMAGE_DIR.iterdir():
          if path.is_file():
            remove_image(path.name)
    elif not database.select('SELECT login FROM users LIMIT 1'):
      users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users", timeout=30)
    else:
      users = None

    if users is not None:
      values = [(user['login'], (user.get('image') or {}).get('link'), user['updated_at']) for user in users]
      database.executemany('INSERT OR IGNORE INTO users (login, link, updated_at) VALUES (?, ?, ?)', values)

    pending = database.select('SELECT * FROM users WHERE link IS NOT NULL')
    print(f'Checking cached images for {len(pending)} users', flush=True)
    completed = unavailable = failed = 0
    for user in pending:
      with image_lock:
        # A login request may already have downloaded this image.
        current = database.select('SELECT * FROM users WHERE login = ?', (user['login'],))[0]
        if current['filename'] and (IMAGE_DIR / current['filename']).is_file():
          continue
        try:
          filename = database.cache_user(current['login'], current['link'], current['updated_at'], ic)
          if filename:
            completed += 1
          else:
            unavailable += 1
        except (ValueError, OSError, Error, requests.RequestException):
          failed += 1
          LOG.warning('Could not cache image for %s', user['login'])
      if (completed + unavailable + failed) % 100 == 0:
        print(f'Image import: {completed} downloaded, {unavailable} unavailable, {failed} failed', flush=True)
    print(f'Image import complete: {completed} downloaded, {unavailable} unavailable, {failed} failed', flush=True)

class Db:
  def __init__(self):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)
    legacy_path = Path('db.sqlite3').resolve()
    migrate_legacy = not DATABASE_PATH.exists() and legacy_path.is_file() and legacy_path != DATABASE_PATH
    self.conn = self.create_connection(DATABASE_PATH)
    if migrate_legacy and self.conn is not None:
      legacy_conn = sqlite3.connect(legacy_path)
      try:
        legacy_conn.backup(self.conn)
      finally:
        legacy_conn.close()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.conn.close()

  def cache_user(self, login, link, updated_at, client):
    with image_lock:
      previous = self.select('SELECT filename FROM users WHERE login = ?', (login,))
      try:
        filename = download_image(link, client) if link else None
      except requests.HTTPError as error:
        has_saved_image = previous and previous[0]['filename'] and (IMAGE_DIR / previous[0]['filename']).is_file()
        if error.response is None or error.response.status_code != 404 or has_saved_image:
          raise
        # Remember a confirmed missing image until the provider's user record changes.
        filename = link = None
      try:
        self.execute('''
          INSERT INTO users (login, link, filename, updated_at) VALUES (?, ?, ?, ?)
          ON CONFLICT(login) DO UPDATE SET
            link = excluded.link, filename = excluded.filename, updated_at = excluded.updated_at
        ''', (login, link, filename, updated_at))
      except Error:
        remove_image(filename)
        raise
      if previous and previous[0]['filename'] != filename:
        remove_image(previous[0]['filename'])
      return filename

  def create_connection(self, db_file):
    return sqlite3.connect(db_file)

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
    except Error:
      self.conn.rollback()
      raise

  def executemany(self, sql, values):
    if self.conn is None:
      return

    try:
      c = self.conn.cursor()
      c.executemany(sql, values)
      self.conn.commit()
    except Error:
      self.conn.rollback()
      raise

  def create_db(self):
    self.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        login TEXT UNIQUE,
        link TEXT,
        filename TEXT,
        updated_at TEXT
      );
    """)
    columns = self.select('PRAGMA table_info(users)')
    if not any(column['name'] == 'filename' for column in columns):
      self.execute('ALTER TABLE users ADD COLUMN filename TEXT')

  def destroy(self):
    self.execute('DROP TABLE users;')


db = Db()
