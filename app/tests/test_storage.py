import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


APP_DIR = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def run_isolated(self, code):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PYTHONPATH=str(APP_DIR), DATA_DIR=str(Path(directory) / 'data'))
            result = subprocess.run(
                [sys.executable, '-c', code], cwd=directory, env=env,
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fresh_database(self):
        self.run_isolated('''
from utils.db import db
from utils.storage import DATABASE_PATH, IMAGE_DIR
db.create_db()
assert DATABASE_PATH.is_file()
assert IMAGE_DIR.is_dir()
assert {r['name'] for r in db.select('PRAGMA table_info(users)')} == {
    'id', 'login', 'link', 'filename', 'updated_at'
}
''')

    def test_legacy_copy_and_schema_migration_are_repeatable(self):
        self.run_isolated('''
import sqlite3
from pathlib import Path
legacy = sqlite3.connect('db.sqlite3')
legacy.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, login TEXT UNIQUE, link TEXT, updated_at TEXT)')
legacy.execute('INSERT INTO users VALUES (7, ?, ?, ?)', ('student', 'https://example.com/image.png', '2026-11-01T00:00:00.000Z'))
legacy.commit()
legacy.close()
from utils.db import db, Db
db.create_db()
row = db.select('SELECT * FROM users')[0]
assert row == dict(id=7, login='student', link='https://example.com/image.png', updated_at='2026-11-01T00:00:00.000Z', filename=None)
assert Path('db.sqlite3').is_file()
db.execute('UPDATE users SET filename = ?', ('student.png',))
db.conn.close()
reopened = Db()
reopened.create_db()
assert reopened.select('SELECT filename FROM users')[0]['filename'] == 'student.png'
assert len(reopened.select('SELECT * FROM users')) == 1
''')

    def test_existing_data_directory_database_is_migrated(self):
        self.run_isolated('''
import os
import sqlite3
from pathlib import Path
data_dir = Path(os.environ['DATA_DIR'])
data_dir.mkdir()
conn = sqlite3.connect(data_dir / 'db.sqlite3')
conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, login TEXT UNIQUE, link TEXT, updated_at TEXT)')
conn.execute("INSERT INTO users (login) VALUES ('existing')")
conn.commit()
conn.close()
from utils.db import db
db.create_db()
assert db.select('SELECT login, filename FROM users') == [{'login': 'existing', 'filename': None}]
''')


if __name__ == '__main__':
    unittest.main()
