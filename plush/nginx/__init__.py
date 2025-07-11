from logging import getLogger
from pathlib import Path

from plush.config import Config, load_config
from plush.constants import (
    NGINX_HTTP_DEFAULT_CONF,
    NGINX_HTTP_SERVER_DIR,
    NGINX_HTTP_UPSTREAM_DIR,
    NGINX_STREAM_SERVER_DIR,
    NGINX_STREAM_UPSTREAM_DIR,
)
from plush.nginx.http_default import GenerateHttpDefaultConf
from plush.nginx.http_server import GenerateOneHttpServerConf
from plush.nginx.stream_server import GenerateOneStreamServerConf
from plush.nginx.upstream import GenerateOneUpstreamConf

logger = getLogger(__name__)


class NginxGenerator:
    CONFIG_NGINX_TOML: str
    NGINX_CONF_DIR: str

    config: Config

    def __init__(self, config_nginx_toml: str, nginx_conf_dir: str):
        self.CONFIG_NGINX_TOML = config_nginx_toml
        self.NGINX_CONF_DIR = nginx_conf_dir
        self.NGINX_HTTP_DEFAULT_CONF = Path(self.NGINX_CONF_DIR).joinpath(
            NGINX_HTTP_DEFAULT_CONF
        )
        self.NGINX_HTTP_UPSTREAM_DIR = Path(self.NGINX_CONF_DIR).joinpath(
            NGINX_HTTP_UPSTREAM_DIR
        )
        self.NGINX_HTTP_SERVER_DIR = Path(self.NGINX_CONF_DIR).joinpath(
            NGINX_HTTP_SERVER_DIR
        )
        self.NGINX_STREAM_UPSTREAM_DIR = Path(self.NGINX_CONF_DIR).joinpath(
            NGINX_STREAM_UPSTREAM_DIR
        )
        self.NGINX_STREAM_SERVER_DIR = Path(self.NGINX_CONF_DIR).joinpath(
            NGINX_STREAM_SERVER_DIR
        )

    def __call__(self, *args, **kwargs):
        # parse nginx.toml
        self.config = load_config(self.CONFIG_NGINX_TOML)

        logger.info(f"Generate {self.NGINX_HTTP_SERVER_DIR}/*.conf ...")
        # generate http_default.conf
        GenerateHttpDefaultConf(
            http_default=self.config.http_default,
            full_path=self.NGINX_HTTP_DEFAULT_CONF,
        ).generate()

        # parser/generate http_upstream.d/*.conf
        if self.config.http_upstream:
            logger.info(f"Generate {self.NGINX_HTTP_UPSTREAM_DIR}/*.conf ...")

            self.prepair_conf_file_path(path=self.NGINX_HTTP_UPSTREAM_DIR)
            for http_upstream in self.config.http_upstream:
                GenerateOneUpstreamConf(
                    upstream=http_upstream,
                    base_path=self.NGINX_HTTP_UPSTREAM_DIR,
                ).generate()

        # parser/generate http_server.d/*.conf
        if self.config.http_server:
            logger.info(f"Generate {self.NGINX_HTTP_SERVER_DIR}/*.conf ...")

            self.prepair_conf_file_path(path=self.NGINX_HTTP_SERVER_DIR)
            for http_server in self.config.http_server:
                GenerateOneHttpServerConf(
                    server=http_server,
                    ssl_cert=self.config.ssl_cert,
                    base_path=self.NGINX_HTTP_SERVER_DIR,
                ).generate()

        # parser/generate stream_upstream.d/*.conf
        if self.config.stream_upstream:
            logger.info(f"Generate {self.NGINX_STREAM_UPSTREAM_DIR}/*.conf ...")

            self.prepair_conf_file_path(path=self.NGINX_STREAM_UPSTREAM_DIR)
            for stream_upstream in self.config.stream_upstream:
                GenerateOneUpstreamConf(
                    upstream=stream_upstream,
                    base_path=self.NGINX_STREAM_UPSTREAM_DIR,
                ).generate()

        # parser/generate stram_server.d/*.conf
        if self.config.stream_server:
            logger.info(f"Generate {self.NGINX_STREAM_SERVER_DIR}/*.conf ...")

            self.prepair_conf_file_path(path=self.NGINX_STREAM_SERVER_DIR)
            for stream_server in self.config.stream_server:
                GenerateOneStreamServerConf(
                    server=stream_server,
                    ssl_cert=self.config.ssl_cert,
                    base_path=self.NGINX_STREAM_SERVER_DIR,
                ).generate()

    def prepair_conf_file_path(self, path: Path):
        if not path.exists():
            path.mkdir(parents=True)

        if not path.is_dir():
            raise

        for file_path in path.iterdir():
            if not file_path.is_file() or file_path.suffix != ".conf":
                continue

            try:
                file_path.unlink()
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
