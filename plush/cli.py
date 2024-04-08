from logging import getLogger

import click

from plush.constants import CONFIG_NGINX_TOML, NGINX_CONF_DIR
from plush.nginx_generate import NginxGenerator
from plush.worker import worker_main

logger = getLogger(__name__)


@click.group()
def cli(**cli_kwargs):
    # do something
    return


@cli.command("worker", help="task worker")
def worker(**cli_kwargs):
    worker_main()


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
