import os

import click
import uvicorn

from utils.db import db

def check__envs():
    errors = []

    for e in ["FT_ID", "FT_SECRET", "CAMPUS_ID", "ENV"]:
        if e not in os.environ:
            errors.append(e)

    if errors:
        raise Exception(f"Missing environment variables: {', '.join(errors)}")


@click.command()
@click.option(
  "--env",
  type=click.Choice(["dev", "prod"], case_sensitive=False),
  default="dev",
  required=True,
)
def main(env):
    os.environ['ENV'] = env
    check__envs()

    db.create_db()
    db.populate_users()

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