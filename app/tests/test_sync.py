import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SETUP = '''
import asyncio
import itertools
import sqlite3
import requests
from unittest.mock import patch
from fastapi import HTTPException
from routers import api, root
from utils.db import db, populate_users
from utils.storage import IMAGE_DIR

db.create_db()
old_time = '2026-11-01T00:00:00.000Z'
new_time = '2026-11-02T00:00:00.000Z'
counter = itertools.count()

def user(login, timestamp=new_time):
    return dict(login=login, image={'link': 'https://example.com/' + login}, updated_at=timestamp)

def download(url, client):
    filename = str(next(counter)) + '.png'
    (IMAGE_DIR / filename).write_bytes(url.encode())
    return filename

def saved(login):
    return db.select('SELECT * FROM users WHERE login = ?', (login,))[0]
'''


class SyncTests(unittest.TestCase):
    def run_isolated(self, code):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]),
                       DATA_DIR=str(Path(directory) / 'data'),
                       FT_ID='test', FT_SECRET='test', CAMPUS_ID='13')
            result = subprocess.run([sys.executable, '-c', SETUP + code],
                                    cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_backfill_and_retry(self):
        self.run_isolated('''
failed = True
def flaky_download(url, client):
    if failed and url.endswith('/retry'):
        raise ValueError('provider error')
    return download(url, client)

with patch('utils.db.IntraAPIClient') as client, patch('utils.db.download_image', side_effect=flaky_download) as images:
    client.return_value.pages_threaded.return_value = [user('good'), user('retry')]
    populate_users()
    good_filename = saved('good')['filename']
    assert (IMAGE_DIR / good_filename).is_file()
    assert saved('retry')['filename'] is None
    failed = False
    populate_users()
    assert saved('good')['filename'] == good_filename
    assert (IMAGE_DIR / saved('retry')['filename']).is_file()
    assert images.call_count == 3
    assert client.return_value.pages_threaded.call_count == 1
    (IMAGE_DIR / good_filename).unlink()
    populate_users()
    assert (IMAGE_DIR / saved('good')['filename']).is_file()
    assert images.call_count == 4
''')

    def test_replacement_and_failed_database_write_preserve_old_image(self):
        self.run_isolated('''
with patch('utils.db.download_image', side_effect=download):
    original = db.cache_user('student', 'https://example.com/old', old_time, None)
with patch('utils.db.download_image', side_effect=ValueError('failed')):
    try:
        db.cache_user('student', 'https://example.com/new', new_time, None)
    except ValueError:
        pass
    else:
        raise AssertionError('Download should have failed')
assert saved('student')['filename'] == original
assert saved('student')['updated_at'] == old_time
assert (IMAGE_DIR / original).is_file()

with patch('utils.db.download_image', side_effect=download), patch.object(db, 'execute', side_effect=sqlite3.OperationalError('write failed')):
    try:
        db.cache_user('student', 'https://example.com/new', new_time, None)
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError('Write should have failed')
assert list(IMAGE_DIR.iterdir()) == [IMAGE_DIR / original]

with patch('utils.db.download_image', side_effect=download):
    replacement = db.cache_user('student', 'https://example.com/new', new_time, None)
assert saved('student')['filename'] == replacement
assert saved('student')['updated_at'] == new_time
assert not (IMAGE_DIR / original).exists()
assert (IMAGE_DIR / replacement).is_file()
db.cache_user('student', None, new_time, None)
assert saved('student')['filename'] is None
assert not (IMAGE_DIR / replacement).exists()
''')

    def test_update_retries_failure_at_shared_timestamp(self):
        self.run_isolated('''
with patch('utils.db.download_image', side_effect=download):
    for login in ('a', 'b', 'c'):
        db.cache_user(login, 'https://example.com/old/' + login, old_time, None)
original_b = saved('b')['filename']
failed = True
def flaky_download(url, client):
    if failed and url.endswith('/b'):
        raise ValueError('provider error')
    return download(url, client)

with patch.object(api, '_get_users', return_value=[user('a'), user('b'), user('c')]), patch('utils.db.download_image', side_effect=flaky_download) as images:
    result = asyncio.run(api.update())
    assert 'incomplete' in result['status']
    assert saved('a')['updated_at'] == new_time
    assert saved('b')['filename'] == original_b
    assert saved('c')['updated_at'] == old_time
    latest = db.select('SELECT * FROM users ORDER BY updated_at DESC LIMIT 1')[0]
    assert api._range(latest).startswith(new_time + ',')
    failed = False
    assert asyncio.run(api.update()) == {'status': 'updated'}
    assert images.call_count == 4
    assert all(saved(login)['updated_at'] == new_time for login in ('a', 'b', 'c'))
    assert asyncio.run(api.update()) == {'status': 'already up-to-date'}
    assert images.call_count == 4
''')

    def test_reset_rebuilds_cache_and_keeps_data_if_api_fetch_fails(self):
        self.run_isolated('''
with patch('utils.db.download_image', side_effect=download):
    old_filename = db.cache_user('old', 'https://example.com/old', old_time, None)
with patch('utils.db.IntraAPIClient') as client:
    client.return_value.pages_threaded.side_effect = ValueError('API failed')
    try:
        populate_users(reset=True)
    except ValueError:
        pass
    else:
        raise AssertionError('Fetch should have failed')
assert saved('old')['filename'] == old_filename
assert (IMAGE_DIR / old_filename).is_file()

with patch('utils.db.IntraAPIClient') as client, patch('utils.db.download_image', side_effect=download):
    client.return_value.pages_threaded.return_value = [user('new')]
    populate_users(reset=True)
assert db.select('SELECT login FROM users') == [{'login': 'new'}]
assert not (IMAGE_DIR / old_filename).exists()
assert list(IMAGE_DIR.iterdir()) == [IMAGE_DIR / saved('new')['filename']]
''')

    def test_missing_user_lookup_saves_local_image_and_preserves_campus_filter(self):
        self.run_isolated('''
with patch.object(root, 'IntraAPIClient') as client, patch('utils.db.download_image', side_effect=download):
    client.return_value.get.return_value.json.return_value = [user('new')]
    response = asyncio.run(root.login('new'))
    assert response.path.is_file()
    assert saved('new')['updated_at'] == new_time
    client.return_value.get.assert_called_once_with('campus/13/users', params={'filter[login]': 'new'}, timeout=30)
    client.return_value.get.reset_mock()
    response = asyncio.run(root.login('new'))
    client.return_value.get.assert_not_called()
    client.return_value.get.return_value.json.return_value = []
    try:
        asyncio.run(root.login('unknown'))
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError('Unknown login should return 404')
    client.return_value.get.return_value.json.return_value = [{'login': 'noimage', 'image': {'link': None}}]
    try:
        asyncio.run(root.login('noimage'))
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError('Missing image should return 404')
''')

    def test_provider_404_is_remembered_without_removing_an_existing_photo(self):
        self.run_isolated('''
from utils.intra import IntraAPIClient
response = requests.Response()
response.status_code = 404
client = IntraAPIClient('test', 'test')
client.token = 'test'
try:
    client.request(lambda *args, **kwargs: response, 'https://example.com/missing')
except requests.HTTPError as error:
    assert error.response.status_code == 404
else:
    raise AssertionError('Expected typed HTTP 404')

db.execute('INSERT INTO users (login, link, updated_at) VALUES (?, ?, ?)', ('missing', 'https://example.com/missing', new_time))
with patch('utils.db.download_image', side_effect=requests.HTTPError(response=response)) as images:
    for attempt in range(2):
        try:
            asyncio.run(root.login('missing'))
        except HTTPException as error:
            assert error.status_code == 404
        else:
            raise AssertionError('Expected local HTTP 404')
    assert images.call_count == 1
assert saved('missing')['filename'] is None
assert saved('missing')['link'] is None
with patch.object(api, '_get_users', return_value=[user('missing')]), patch('utils.db.download_image') as images:
    assert asyncio.run(api.update()) == {'status': 'already up-to-date'}
    images.assert_not_called()

with patch('utils.db.download_image', side_effect=download):
    filename = db.cache_user('existing', 'https://example.com/existing', old_time, None)
with patch('utils.db.download_image', side_effect=requests.HTTPError(response=response)):
    try:
        db.cache_user('existing', 'https://example.com/missing', new_time, None)
    except requests.HTTPError:
        pass
    else:
        raise AssertionError('Missing replacement should fail')
assert saved('existing')['filename'] == filename
assert saved('existing')['updated_at'] == old_time
assert (IMAGE_DIR / filename).is_file()
''')
