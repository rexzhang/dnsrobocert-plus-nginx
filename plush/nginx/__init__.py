from logging import getLogger
from pathlib import Path

from ..config import Config, get_config_from_file
from ..constants import (
    NGINX_HTTP_DEFAULT_CONF,
    NGINX_HTTP_SERVER_DIR,
    NGINX_HTTP_UPSTREAM_DIR,
    NGINX_MAIL_SERVER_DIR,
    NGINX_STREAM_SERVER_DIR,
    NGINX_STREAM_UPSTREAM_DIR,
)
from ..deploy_stage import get_file_path
from .http_default import GenerateHttpDefaultConf
from .http_server import GenerateOneHttpServerConf
from .mail_server import GenerateOneMailServerConf
from .stream_server import GenerateOneStreamServerConf
from .upstream import GenerateOneUpstreamConf

logger = getLogger(__name__)


class NginxGenerator:
    config: Config

    def __init__(self, config_nginx_toml: Path, nginx_conf_dir: Path):
        self.CONFIG_NGINX_TOML = config_nginx_toml
        self.NGINX_CONF_DIR = get_file_path(nginx_conf_dir)
        self.prepair_conf_file_path(self.NGINX_CONF_DIR)

        self.NGINX_HTTP_DEFAULT_CONF = self.NGINX_CONF_DIR.joinpath(
            NGINX_HTTP_DEFAULT_CONF
        )
        self.NGINX_HTTP_UPSTREAM_DIR = self.NGINX_CONF_DIR.joinpath(
            NGINX_HTTP_UPSTREAM_DIR
        )
        self.NGINX_HTTP_SERVER_DIR = self.NGINX_CONF_DIR.joinpath(NGINX_HTTP_SERVER_DIR)
        self.NGINX_STREAM_UPSTREAM_DIR = self.NGINX_CONF_DIR.joinpath(
            NGINX_STREAM_UPSTREAM_DIR
        )
        self.NGINX_STREAM_SERVER_DIR = self.NGINX_CONF_DIR.joinpath(
            NGINX_STREAM_SERVER_DIR
        )
        self.NGINX_MAIL_SERVER_DIR = self.NGINX_CONF_DIR.joinpath(NGINX_MAIL_SERVER_DIR)

    def __call__(self, *args, **kwargs):
        # parse nginx.toml
        self.config = get_config_from_file(self.CONFIG_NGINX_TOML)

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

        # parser/generate mail_server.d/*.conf
        if self.config.stream_server:
            logger.info(f"Generate {self.NGINX_MAIL_SERVER_DIR}/*.conf ...")

            self.prepair_conf_file_path(path=self.NGINX_MAIL_SERVER_DIR)
            for mail_server in self.config.mail_server:
                GenerateOneMailServerConf(
                    server=mail_server,
                    ssl_cert=self.config.ssl_cert,
                    base_path=self.NGINX_MAIL_SERVER_DIR,
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
