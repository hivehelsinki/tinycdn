import threading

from fastapi import APIRouter
from utils.db import db, populate_users

router = APIRouter()

@router.get('/health')
async def health():
    return {'status': 'alive'}

@router.get('/update')
async def update():
    pass

@router.get('/reset')
async def reset():
    db.destroy()
    db.create_db()
    thread = threading.Thread(target=populate_users)
    thread.start()
    return {'status': 'resetting database'}

