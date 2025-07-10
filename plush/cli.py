from logging import getLogger

import click

from plush.constants import CONFIG_NGINX_TOML, NGINX_CONF_DIR
from plush.nginx import NginxGenerator
from plush.worker import ScheduleDaemon

logger = getLogger(__name__)


@click.group()
def cli(**cli_kwargs):
    # do something
    return


@cli.group(help="Task Worker")
def worker(**cli_kwargs):
    pass


@worker.command("start", help="Start Worker")
def worker_start(**cli_kwargs):
    ScheduleDaemon().start()


@worker.command("stop", help="Stop Worker")
def worker_stop(**cli_kwargs):
    ScheduleDaemon().stop()


@cli.command("generate", help="nginx *.conf generator")
@click.option(
    "--config-nginx-toml",
    default=CONFIG_NGINX_TOML,
    type=str,
    help=f"[default:{CONFIG_NGINX_TOML}]",
)
@click.option(
    "--nginx-conf-dir",
    default=NGINX_CONF_DIR,
    type=str,
    help=f"[default:{NGINX_CONF_DIR}]",
)
def generator(**cli_kwargs):
    NginxGenerator(**cli_kwargs)()


def main():
    cli()
