import os
import threading

from fastapi import APIRouter
from datetime import datetime
from dateutil.relativedelta import relativedelta

from utils.db import db, populate_users
from utils.intra import IntraAPIClient

router = APIRouter()

def _toutc(str):
    return datetime.strptime(str, "%Y-%m-%dT%H:%M:%S.%fZ")

def _range(row):
    updated_at = _toutc(row['updated_at']) + relativedelta(seconds=1)
    return f"{updated_at},{datetime.utcnow()}"

def _get_users(row):
    ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
    users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users?range[updated_at]={_range(row)}")
    
    return users

@router.get('/health')
async def health():
    return {'status': 'alive'}

@router.get('/update')
async def update():
    in_db = db.select('SELECT * FROM users ORDER BY updated_at DESC LIMIT 1')
    if not in_db:
        return {'status': 'database is empty, please reset it first'}

    users = _get_users(in_db[0])
    if users:
        values = [(user['login'], user['image']['link'], user['updated_at']) for user in users]
        db.executemany('INSERT OR REPLACE INTO users (login, link, updated_at) VALUES (?, ?, ?)', values)
        return {'status': 'updated'}
    else:
        return {'status': 'already up-to-date'}

@router.get('/reset')
async def reset():
    db.destroy()
    db.create_db()
    thread = threading.Thread(target=populate_users)
    thread.start()
    return {'status': 'resetting database'}

