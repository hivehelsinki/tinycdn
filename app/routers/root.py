import os
import requests

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from sqlite3 import Error
from utils.db import Db, image_lock
from utils.intra import IntraAPIClient
from utils.storage import IMAGE_DIR

router = APIRouter()

@router.get('/favicon.ico')
async def favicon():
    return FileResponse('favicon.ico')

@router.get('/{login}')
async def login(login):
    return await run_in_threadpool(_login, login)


def _login(login):
    # The worker thread owns both the blocking downloads and its SQLite connection.
    with Db() as database:
        rows = database.select('SELECT * FROM users WHERE login = ? LIMIT 1', (login,))
        if rows and rows[0]['filename'] and (IMAGE_DIR / rows[0]['filename']).is_file():
            return FileResponse(IMAGE_DIR / rows[0]['filename'])

        ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
        try:
            if rows:
                user = rows[0]
            else:
                # Preserve the existing restriction to our campus' students.
                users = ic.get(
                    f"campus/{os.environ['CAMPUS_ID']}/users",
                    params={'filter[login]': login}, timeout=30,
                ).json()
                if not users:
                    raise HTTPException(status_code=404, detail="user not found in database")
                user = dict(login=users[0]['login'], link=(users[0].get('image') or {}).get('link'),
                            updated_at=users[0].get('updated_at'))
            if not user['link']:
                raise HTTPException(status_code=404, detail="user has no image")
            with image_lock:
                # Import or another request may have filled the cache while we waited.
                current = database.select('SELECT filename FROM users WHERE login = ?', (user['login'],))
                if current and current[0]['filename'] and (IMAGE_DIR / current[0]['filename']).is_file():
                    filename = current[0]['filename']
                else:
                    filename = database.cache_user(user['login'], user['link'], user['updated_at'], ic)
        except (requests.RequestException, ValueError, OSError, Error):
            raise HTTPException(status_code=502, detail="could not download user image")
        if not filename:
            raise HTTPException(status_code=404, detail="user has no image")
        return FileResponse(IMAGE_DIR / filename)
