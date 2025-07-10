import tomllib
from dataclasses import dataclass, field
from logging import getLogger
from typing import Annotated
from dataclass_wizard import JSONWizard
from dataclass_wizard.v1 import Alias

logger = getLogger(__name__)


@dataclass
class Common:
    ssl_cert_domain: str


@dataclass
class Upstream:
    # 配置文件兼容 http upstream 和 stream upstream
    enable: bool = True

    name: str = ""
    content: str = ""


@dataclass
class ServerAbc:
    enable: bool = True

    listen: int | None = None
    listen_ssl: int | None = None

    ssl_cert_domain: str | None = None

    upstream_name: str | None = None
    upstream_server: str | None = None


@dataclass
class HttpServer(ServerAbc):
    server_name: str = ""

    listen_http2: bool = True
    listen_ipv6: bool = True

    root_path: str | None = None
    proxy_pass: str | None = None
    location: dict[str, str] = field(default_factory=dict)

    client_max_body_size: str | None = None
    support_websocket: bool = False
    hsts: bool = False
    hsts_max_age: int = 31536000

    @property
    def name(self) -> str:
        return self.server_name


@dataclass
class StreamServer(ServerAbc):
    comment: str = "---"

    proxy_pass: str = ""

    @property
    def name(self) -> str:
        data = list()
        if self.listen:
            data.append(f"p{self.listen}")
        if self.listen_ssl:
            data.append(f"p{self.listen_ssl}")

        result = "_".join(data)
        if not result:
            result = "?"

        return result


@dataclass
class Config(JSONWizard):
    class _(JSONWizard.Meta):
        v1 = True

    common: Annotated[Common, Alias("default")]  # => common

    http_upstream: list[Upstream] = field(default_factory=list)
    http_server: Annotated[list[HttpServer], Alias("http_d")] = field(
        default_factory=list
    )

    stream_server: Annotated[list[StreamServer], Alias("stream_d")] = field(
        default_factory=list
    )


def load_config(toml_file: str) -> Config:
    # parse nginx.toml
    try:
        with open(toml_file, "rb") as f:
            config_obj = tomllib.load(f)

    except FileNotFoundError as e:
        logger.critical(f"Open file {toml_file} failed, {e}")
        exit(1)
    except tomllib.TOMLDecodeError as e:
        logger.critical(f"Parse file {toml_file} failed, {e}")
        exit(1)

    # convert to Config
    try:
        config = Config.from_dict(config_obj)
    except TypeError as e:
        logger.critical(f"Parse file {toml_file} failed, {e}")
        exit(1)

    return config
