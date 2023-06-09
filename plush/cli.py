from logging import getLogger

import click

from plush.nginx_generate import NginxGenerator

logger = getLogger(__name__)

DEFAULT_NGINX_TOML = "/config/nginx.toml"
DEFAULT_HTTP_D_DIR = "/data/nginx/http.d"
DEFAULT_STREAM_D_DIR = "/data/nginx/stream.d"


@click.group()
def cli(**cli_kwargs):
    # do something
    return


@cli.command("check", help="system checker")
def runserver(**cli_kwargs):
    pass


@cli.command("generate", help="nginx *.conf generator")
@click.option(
    "--nginx-toml",
    default=DEFAULT_NGINX_TOML,
    type=str,
    help=f"[default:{DEFAULT_NGINX_TOML}]",
)
@click.option(
    "--http-d-dir",
    default=DEFAULT_HTTP_D_DIR,
    type=str,
    help=f"[default:{DEFAULT_HTTP_D_DIR}]",
)
@click.option(
    "--stream-d-dir",
    default=DEFAULT_STREAM_D_DIR,
    type=str,
    help=f"[default:{DEFAULT_STREAM_D_DIR}]",
)
def generator(**cli_kwargs):
    NginxGenerator(**cli_kwargs)()


def main():
    cli()
