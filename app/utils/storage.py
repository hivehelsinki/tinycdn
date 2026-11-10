import os
from pathlib import Path


DATA_DIR = Path(os.environ.get('DATA_DIR', 'data')).resolve()
IMAGE_DIR = DATA_DIR / 'images'
DATABASE_PATH = DATA_DIR / 'db.sqlite3'
