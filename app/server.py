import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from intra import ic

def create_app():
  app_ = FastAPI(
    title='TinyCDN',
    description="TinyCDN is a simple CDN for students' profile pictures",
    version="0.0.1",
    docs_url=None if os.environ['ENV'] == 'prod' else '/docs',
    redoc_url=None if os.environ['ENV'] == 'prod' else '/redoc',
  )

  @app_.get('/api/reset')
  async def reset():
      return {'message': 'Reset'}

  @app_.get('/api/force_reset')
  async def force_reset():
      return {'message': 'Force Reset'}

  @app_.get('/api/health')
  async def health():
      return {'message': 'success'}

  @app_.get('/')
  async def root():
      return {'app': app_.title, 'version': app_.version}

  @app_.get('/{login}')
  async def user(login):
      try:
        res = ic.get(f'users/{login}').json()
        return RedirectResponse(res['image']['link'])
      except Exception as e:
        raise HTTPException(status_code=404, detail="user or picture not found")


  return app_


app = create_app()