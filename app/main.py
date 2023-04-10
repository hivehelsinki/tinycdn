import os

import click
import uvicorn

from intra import ic
from db import db

@click.command()
@click.option(
  "--env",
  type=click.Choice(["dev", "prod"], case_sensitive=False),
  default="dev",
)
def main(env):
    os.environ['ENV'] = env

    db.create_db()

    print("Fetching users from intranet")
    users = ic.pages_threaded(f"campus/{os.environ['CAMPUS_ID']}/users")
    values = [(user['login'], user['image']['link']) for user in users]
    db.executemany('INSERT OR IGNORE INTO users (login, link) VALUES (?, ?)', values)

    uvicorn.run(
        app="server:app",
        host='0.0.0.0',
        port=8000,
        reload=True if os.environ['ENV'] != "prod" else False,
        log_level="warning" if os.environ['ENV'] == "prod" else "debug",
        workers=1,
    )

if __name__ == "__main__":
    main()