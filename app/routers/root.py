from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, FileResponse

from utils.db import db

router = APIRouter()

@router.get('/favicon.ico')
async def favicon():
    return FileResponse('favicon.ico')

@router.get('/{login}')
async def login(login):
    res = db.select('SELECT * FROM users WHERE login = ? LIMIT 1', (login,))
    if res:
        return RedirectResponse(res[0]['link'])
    else:
        # instead of raising here, might be better to fetch api and insert in db.
        raise HTTPException(status_code=404, detail="user not found in database")