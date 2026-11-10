import os
import threading
import requests
from sqlite3 import Error

from fastapi import APIRouter
from datetime import datetime, timezone
from starlette.concurrency import run_in_threadpool

from utils.db import Db, populate_users, sync_lock
from utils.intra import IntraAPIClient
from utils.storage import IMAGE_DIR

router = APIRouter()

def _range(row):
    # Include the boundary so users sharing a timestamp can be retried after failures.
    return f"{row['updated_at']},{datetime.now(timezone.utc).isoformat()}"

def _get_users(row, ic):
    users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users",
                             params={'range[updated_at]': _range(row)}, timeout=30)
    
    return users

@router.get('/health')
async def health():
    return {'status': 'alive'}

@router.get('/update')
async def update():
    return await run_in_threadpool(_update)


def _update():
    with sync_lock, Db() as database:
        in_db = database.select('SELECT * FROM users WHERE updated_at IS NOT NULL ORDER BY updated_at DESC LIMIT 1')
        if not in_db:
            return {'status': 'database is empty, please reset it first'}

        ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
        users = _get_users(in_db[0], ic)
        updated = False
        # Stop at the first failed download so the update boundary cannot skip it.
        for user in sorted(users, key=lambda user: user['updated_at']):
            link = (user.get('image') or {}).get('link')
            existing = database.select('SELECT * FROM users WHERE login = ?', (user['login'],))
            if existing and existing[0]['updated_at'] == user['updated_at']:
                known_missing = not existing[0]['link'] and not existing[0]['filename']
                cached = existing[0]['link'] == link and existing[0]['filename'] and (IMAGE_DIR / existing[0]['filename']).is_file()
                if known_missing or cached:
                    continue
            try:
                database.cache_user(user['login'], link, user['updated_at'], ic)
            except (requests.RequestException, ValueError, OSError, Error):
                return {'status': 'update incomplete; retry /api/update'}
            updated = True
        return {'status': 'updated' if updated else 'already up-to-date'}

@router.get('/reset')
async def reset():
    thread = threading.Thread(target=populate_users, kwargs={'reset': True}, daemon=True)
    thread.start()
    return {'status': 'resetting database'}

