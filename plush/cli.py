from logging import getLogger
from pathlib import Path

import typer

from . import __version__
from .constants import CONFIG_NGINX_TOML, NGINX_CONF_DIR
from .crontab import update_crontab_file
from .logrotate import generate_logrotate_conf
from .nginx import NginxGenerator
from .worker import ScheduleDaemon, task_nginx_reload

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


@app.command("generate", help="generate files")
def generate(
    config_nginx_toml: str = typer.Option(
        CONFIG_NGINX_TOML, help=f"[default:{CONFIG_NGINX_TOML}]"
    )
):
    # generate nginx *.conf
    NginxGenerator(
        config_nginx_toml=Path(config_nginx_toml), nginx_conf_dir=Path(NGINX_CONF_DIR)
    )()

    # generate logrotate.conf file
    generate_logrotate_conf()

    # generate crontab file
    update_crontab_file()


@app.command(help="for crontab")
def cron():
    task_nginx_reload()


def main():
    typer.echo(f"Plush v{__version__}")
    app()
