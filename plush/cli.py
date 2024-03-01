from logging import getLogger

import click

from plush.constants import DEFAULT_CONFIG_NGINX_TOML, DEFAULT_NGINX_CONF_DIR
from plush.nginx_generate import NginxGenerator

logger = getLogger(__name__)


@click.group()
def cli(**cli_kwargs):
    # do something
    return


@cli.command("check", help="system checker")
def runserver(**cli_kwargs):
    pass


@cli.command("generate", help="nginx *.conf generator")
@click.option(
    "--config-nginx-toml",
    default=DEFAULT_CONFIG_NGINX_TOML,
    type=str,
    help=f"[default:{DEFAULT_CONFIG_NGINX_TOML}]",
)
@click.option(
    "--nginx-conf-dir",
    default=DEFAULT_NGINX_CONF_DIR,
    type=str,
    help=f"[default:{DEFAULT_NGINX_CONF_DIR}]",
)
def generator(**cli_kwargs):
    NginxGenerator(**cli_kwargs)()


def main():
    cli()
