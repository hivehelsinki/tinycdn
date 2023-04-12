import os
import click
import uvicorn
from uvicorn.config import LOGGING_CONFIG

def check__envs(env):
  os.environ['ENV'] = env
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
  LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s] %(levelprefix)s %(message)s"
  LOGGING_CONFIG["formatters"]["access"]["fmt"] = '%(asctime)s [%(name)s] %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'

  check__envs(env)

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