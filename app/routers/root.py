import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, FileResponse

from utils.db import db
from utils.intra import IntraAPIClient

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
        ic = IntraAPIClient(os.environ['FT_ID'], os.environ['FT_SECRET'])
        # I'm using campus/:id/users and filter to make sure I'll be catching only our campus' students.
        res = ic.get(f"campus/{os.environ['CAMPUS_ID']}/users?filter[login]={login}").json()
        if res:
            db.execute('INSERT INTO users (login, link) VALUES (?, ?)', (login, res[0]['image']['link']))
            return RedirectResponse(res[0]['image']['link'])
        else:
            raise HTTPException(status_code=404, detail="user not found in database")
