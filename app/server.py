import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from utils.db import db

def create_app():
  app_ = FastAPI(
    title='TinyCDN',
    description="TinyCDN is a simple CDN for students' profile pictures",
    version="0.0.1",
    docs_url=None if os.environ['ENV'] == 'prod' else '/docs',
    redoc_url=None if os.environ['ENV'] == 'prod' else '/redoc',
  )

  @app_.get('/api/health')
  async def health():
      return {'message': 'success'}

  @app_.get('/')
  async def root():
      return {'app': app_.title, 'version': app_.version}

  @app_.get('/{login}')
  async def login(login):
      try:
        res = db.select('SELECT * FROM users WHERE login = ? LIMIT 1', (login,))
        return RedirectResponse(res[0]['link'])
      except Exception as e:
        raise HTTPException(status_code=404, detail="user or picture not found")

  return app_


app = create_app()