import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

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

  @app_.get('/{login}', response_class=RedirectResponse)
  async def user(login):
      return 'https://i.pravatar.cc/300'

  return app_


app = create_app()