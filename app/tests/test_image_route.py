import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ImageRouteTests(unittest.TestCase):
    def test_download_cache_hit_missing_file_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(
                os.environ,
                PYTHONPATH=str(Path(__file__).resolve().parents[1]),
                DATA_DIR=str(Path(directory) / 'data'),
                FT_ID='test', FT_SECRET='test', CAMPUS_ID='13',
            )
            result = subprocess.run([sys.executable, '-c', '''
import asyncio
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.responses import FileResponse
from routers import root
from utils.db import db
from utils.storage import IMAGE_DIR

db.create_db()
db.execute('INSERT INTO users (login, link) VALUES (?, ?)', ('student', 'https://example.com/image'))

def download(url, client):
    (IMAGE_DIR / 'test.png').write_bytes(b'test image')
    return 'test.png'

with patch('utils.db.download_image', side_effect=download) as mocked:
    response = asyncio.run(root.login('student'))
    assert isinstance(response, FileResponse)
    assert response.path.read_bytes() == b'test image'
    assert db.select('SELECT filename FROM users')[0]['filename'] == 'test.png'
    assert mocked.call_count == 1
    response = asyncio.run(root.login('student'))
    assert mocked.call_count == 1
    (IMAGE_DIR / 'test.png').unlink()
    response = asyncio.run(root.login('student'))
    assert response.path.is_file()
    assert mocked.call_count == 2

db.execute('INSERT INTO users (login, link) VALUES (?, ?)', ('failed', 'https://example.com/image'))
with patch('utils.db.download_image', side_effect=ValueError('provider error')):
    try:
        asyncio.run(root.login('failed'))
    except HTTPException as error:
        assert error.status_code == 502
    else:
        raise AssertionError('Expected HTTP 502')
assert db.select('SELECT filename FROM users WHERE login = ?', ('failed',))[0]['filename'] is None
'''], cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
