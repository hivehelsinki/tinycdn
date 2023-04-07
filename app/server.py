import os
import sys
from fastapi import FastAPI

def receive_signal(signalNumber, frame):
    print('Received:', signalNumber)
    sys.exit()

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
      return {'message': 'Healthy'}

  @app_.get('/{login}')
  async def root(login):
      return {'message': login}

  @app_.on_event("startup")
  async def startup_event():
    import signal
    signal.signal(signal.SIGINT, receive_signal)

  return app_


app = create_app()