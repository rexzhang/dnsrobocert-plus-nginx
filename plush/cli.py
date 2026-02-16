from logging import getLogger

import typer

from .constants import CONFIG_NGINX_TOML, NGINX_CONF_DIR
from .nginx import NginxGenerator
from .worker import ScheduleDaemon

logger = getLogger(__name__)

app = typer.Typer()

worker_app = typer.Typer()
app.add_typer(worker_app, name="worker", help="Task Worker")


@worker_app.command("start", help="Start Worker")
def worker_start():
    ScheduleDaemon().start()


@worker_app.command("stop", help="Stop Worker")
def worker_stop():
    ScheduleDaemon().stop()


@app.command("generate", help="nginx *.conf generator")
def generate(
    config_nginx_toml: str = typer.Option(
        CONFIG_NGINX_TOML, help=f"[default:{CONFIG_NGINX_TOML}]"
    ),
    nginx_conf_dir: str = typer.Option(
        NGINX_CONF_DIR, help=f"[default:{NGINX_CONF_DIR}]"
    ),
):
    NginxGenerator(config_nginx_toml=config_nginx_toml, nginx_conf_dir=nginx_conf_dir)()


def main():
    app()
