import os
import threading

from fastapi import FastAPI


from routers import api, root
from utils.db import db, populate_users

async def startup_event():
  thread = threading.Thread(target=populate_users)
  thread.start()

def create_app():
  db.create_db()
  app_ = FastAPI(
    title='TinyCDN',
    description="TinyCDN is a simple CDN for students' profile pictures",
    version="0.0.2",
    docs_url=None if os.environ['ENV'] == 'prod' else '/docs',
    redoc_url=None if os.environ['ENV'] == 'prod' else '/redoc'
  )

  app_.add_event_handler("startup", startup_event)

  @app_.get('/')
  async def home():
    return {'name': app_.title, 'version': app_.version}

  app_.include_router(api.router, prefix='/api', tags=['api'])
  app_.include_router(root.router)

  return app_


app = create_app()