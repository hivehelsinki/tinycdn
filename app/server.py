import asyncio
import os
import threading


from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse

from utils.db import db, populate_users

async def startup_event():
  thread = threading.Thread(target=populate_users)
  thread.start()

def create_app():
  db.create_db()
  app_ = FastAPI(
    title='TinyCDN',
    description="TinyCDN is a simple CDN for students' profile pictures",
    version="0.0.1",
    docs_url=None if os.environ['ENV'] == 'prod' else '/docs',
    redoc_url=None if os.environ['ENV'] == 'prod' else '/redoc'
  )

  app_.add_event_handler("startup", startup_event)

  @app_.get('/api/health')
  async def health():
    return {'message': 'success'}

  @app_.get('/api/update')
  async def update():
    pass

  @app_.get('/')
  async def root():
    return {'name': app_.title, 'version': app_.version}

  @app_.get('/{login}')
  async def login(login):
    try:
      res = db.select('SELECT * FROM users WHERE login = ? LIMIT 1', (login,))
      if res:
        return RedirectResponse(res[0]['link'])
      else:
        # instead of raising here, might be better to fetch api and insert in db.
        raise HTTPException(status_code=404, detail="user not found in database")
    except Exception as e:
      raise HTTPException(status_code=500)

  return app_


app = create_app()