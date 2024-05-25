import builtins
import tomllib
from logging import getLogger
from pathlib import Path
from string import Template

import pydantic

from plush.constants import (
    DNSROBOCERT_SSL_FILE_DIR,
    NGINX_HTTP_CONF,
    NGINX_HTTP_DEFAULT_CONF,
    NGINX_HTTP_PORT,
    NGINX_HTTPS_PORT,
    NGINX_STREAM_CONF,
)

logger = getLogger(__name__)


black_template_default_listen = """
listen $port default_server;
listen [::]:$port default_server;"""

black_template_default_listen_ssl = """
listen $port ssl default_server;
listen [::]:$port ssl default_server;
http2 on;"""

block_template_ssl = """
# SSL certificate
ssl_certificate     $ssl_path_root/fullchain.pem;
ssl_certificate_key $ssl_path_root/privkey.pem;
include /app/nginx/snippets/ssl-params.conf;"""

block_template_websocket = """
# Enable WebSocket Support
include /app/nginx/snippets/websocket.conf;"""

block_template_client_max_body_size = """
# Fix: 413 - Request Entity Too Large
client_max_body_size $client_max_body_size;"""

# https://www.nginx.com/blog/http-strict-transport-security-hsts-and-nginx/
block_template_hsts = """
# Enable HSTS
add_header Strict-Transport-Security "max-age=$hsts_max_age; includeSubDomains" always;"""  # noqa E501

block_template_upstream = """
# upstream server define
upstream $upstream_name {
    server $upstream_server;
}"""

# https://serverfault.com/questions/578648/properly-setting-up-a-default-nginx-server-for-https
http_default_conf_template = """
map "" $$empty {
    default "";
}

server {
    $default_listen

    server_name _;

    return 444;
}

server {
    $default_listen_ssl

    server_name _;

    ssl_ciphers aNULL;
    ssl_certificate data:$$empty;
    ssl_certificate_key data:$$empty;

    return 444;
}
"""

http_conf_template_main_only_http = """
server {
    server_name $server_name;
    $listen

    $values
    $locations
}
"""

http_conf_template_main_only_https = """
$block_upstream
server {
    server_name $server_name;
    $listen_ssl

    $values
    $block_ssl
    $block_hsts
    $locations
}
"""

http_conf_template_main_http_and_https = """
$block_upstream
server {
    server_name $server_name;
    $listen

    return 301 https://$server_name$$request_uri;
}

server {
    $listen_ssl
    server_name $server_name;

    $values

    proxy_buffering off; ## Sends data as fast as it can not buffering large chunks.

    $block_ssl
    $block_hsts
    $locations
}
"""

block_template_location_root_with_root_path = """
    location / {
        root $$root_path;
    }"""

block_template_location_root_with_proxy_pass = """
    location / {
        $block_client_max_body_size

        include /app/nginx/snippets/proxy-params.conf;
        $block_websocket

        proxy_pass $$proxy_pass;
    }"""

block_template_location_custom = """
    location $location_path {
        $location_content
    }"""


stream_conf_template_main_no_ssl = """
$block_upstream
server {
    # $comment
    listen $listen;

    $values

    proxy_pass $$proxy_pass;
}
"""

stream_conf_template_main_only_ssl = """
$block_upstream
server {
    # $comment
    listen $listen_ssl ssl;

    $values

    proxy_ssl on;
    $block_ssl

    proxy_pass $$proxy_pass;
}
"""


class Default(pydantic.BaseModel):
    ssl_cert_domain: str


class ServerAbc(pydantic.BaseModel):
    enable: bool = True

    listen: int | None = None
    listen_ssl: int | None = None

    ssl_cert_domain: str | None = None

    upstream_name: str | None = None
    upstream_server: str | None = None


class HTTPD(ServerAbc):
    server_name: str

    listen_http2: bool = True
    listen_ipv6: bool = True

    root_path: str | None = None
    proxy_pass: str | None = None

    location: dict[str, str] = dict()
    client_max_body_size: str | None = None
    support_websocket: bool = False
    hsts: bool = False
    hsts_max_age: int = 31536000


class StreamD(ServerAbc):
    comment: str = "---"

    proxy_pass: str


class Config(pydantic.BaseModel):
    default: Default
    http_d: list[HTTPD]
    stream_d: list[StreamD] = list()


class ServerGeneratorAbc:
    def __init__(
        self, default: Default, servers: list[HTTPD | StreamD], conf_filename: str
    ):
        self.default = default
        self.server = servers
        self.conf_filename = conf_filename

    def __call__(self, *args, **kwargs) -> str:
        logger.info(f"Generate [{self.conf_filename}]...")

        conf_str = ""

        for server in self.server:
            conf_str += self._generate_one_server(server=server)

        try:
            with open(self.conf_filename, "w") as f:
                f.write(conf_str)
            logger.info(f"Generate [{self.conf_filename}]...DONE")
        except OSError as e:
            logger.critical(f"Generate [{self.conf_filename}] failed, {e}")
            exit(1)

        return conf_str

    def _generate_one_server(self, server: HTTPD | StreamD) -> str:
        raise NotImplementedError


class GenerateOneServerAbc:
    _values: dict = dict()

    def __init__(self, server: HTTPD | StreamD, default: Default):
        self.server = server
        self.default = default

        if server.proxy_pass:
            self.update_value(k="proxy_pass", v=server.proxy_pass)

    def __call__(self, *args, **kwargs) -> str:
        if not self.server.enable:
            logger.info(f"Skip {self.id_str()}")
            return ""

        result = self.generate()
        if result:
            logger.info(f"Generate {self.id_str()}")
            return result

        else:
            # TODO
            return ""

    def update_value(self, k, v):
        self._values[k] = v

    def generate_values_list_str(self) -> str:
        result = "# values list\n"
        for k, v in self._values.items():
            match type(v):
                case builtins.str:
                    result += f'    set ${k} "{v}";\n'
                case builtins.int:
                    result += f"    set ${k} {v};\n"
                case _:
                    raise
        return result

    def generate_block_ssl(self) -> str:
        if self.server.ssl_cert_domain is None:
            ssl_cert_domain = self.default.ssl_cert_domain
        else:
            ssl_cert_domain = self.server.ssl_cert_domain

        if ssl_cert_domain is None:
            # default is None
            return ""

        return Template(block_template_ssl).substitute(
            {
                "ssl_path_root": Path(DNSROBOCERT_SSL_FILE_DIR)
                .joinpath(ssl_cert_domain)
                .as_posix()
            }
        )

    @staticmethod
    def id_str() -> str:
        raise NotImplementedError

    def generate(self) -> str:
        raise NotImplementedError


class GenerateOneServerHTTPD(GenerateOneServerAbc):
    def id_str(self) -> str:
        match (
            self.server.server_name is None,
            self.server.root_path is None,
            self.server.proxy_pass is None,
        ):
            case False, False, True:
                return (
                    f"http.d: [{self.server.root_path}] >> [{self.server.server_name}]"
                )
            case False, True, False:
                return (
                    f"http.d: [{self.server.proxy_pass}] >> [{self.server.server_name}]"
                )

        return "?"

    def generate(self) -> str:
        # httpd location
        locations_str = ""
        if "/" not in self.server.location:
            # create from default template
            if isinstance(self.server.root_path, str):
                self.update_value(k="root_path", v=self.server.root_path)
                locations_str = self._generate_location_root_with_root()
            elif isinstance(self.server.proxy_pass, str):
                self.update_value(k="proxy_pass", v=self.server.proxy_pass)
                locations_str = self._generate_location_root_with_proxy_pass()
            else:
                logger.error(f"{self.id_str()} miss [root_path] and [proxy_pass]")
                return ""

        for k, v in self.server.location.items():
            locations_str += Template(block_template_location_custom).substitute(
                {"location_path": k, "location_content": v}
            )

        # httpd main
        match (
            isinstance(self.server.listen, int),
            isinstance(self.server.listen_ssl, int),
        ):
            case (True, False):
                main_template = Template(http_conf_template_main_only_http)
            case (False, True):
                main_template = Template(http_conf_template_main_only_https)
            case (True, True):
                main_template = Template(http_conf_template_main_http_and_https)
            case _:
                logger.error(f"{self.id_str()} miss [listen] and [listen_ssl]")
                return ""

        match self.server.listen_http2, self.server.listen_ipv6:
            case True, True:
                listen = (
                    f"listen {self.server.listen}; listen [::]:{self.server.listen};"
                )
                listen_ssl = f"listen {self.server.listen_ssl} ssl http2; listen [::]:{self.server.listen_ssl} ssl http2;"  # noqa E501

            case True, False:
                listen = f"listen {self.server.listen};"
                listen_ssl = f"listen {self.server.listen_ssl} ssl http2;"

            case False, True:
                listen = (
                    f"listen {self.server.listen}; listen [::]:{self.server.listen};"
                )
                listen_ssl = f"listen {self.server.listen_ssl} ssl; listen [::]:{self.server.listen_ssl} ssl;"  # noqa E501

            case False, False:
                listen = f"listen {self.server.listen};"
                listen_ssl = f"listen {self.server.listen_ssl} ssl;"

            case _:
                raise

        if self.server.hsts:
            block_hsts = Template(block_template_hsts).substitute(
                {"hsts_max_age": self.server.hsts_max_age}
            )
        else:
            block_hsts = ""

        if self.server.upstream_name and self.server.upstream_server:
            block_upstream = Template(block_template_upstream).substitute(
                {
                    "upstream_name": self.server.upstream_name,
                    "upstream_server": self.server.upstream_server,
                }
            )
        else:
            block_upstream = ""

        result = main_template.substitute(
            {
                "values": self.generate_values_list_str(),
                "server_name": self.server.server_name,
                "listen": listen,
                "listen_ssl": listen_ssl,
                "block_ssl": self.generate_block_ssl(),
                "block_hsts": block_hsts,
                "block_upstream": block_upstream,
                "locations": locations_str,
            }
        )

        return result

    def _generate_location_root_with_root(self) -> str:
        return Template(block_template_location_root_with_root_path).substitute(
            {"root_path": self.server.root_path}
        )

    def _generate_location_root_with_proxy_pass(self) -> str:
        if self.server.client_max_body_size is None:
            block_client_max_body_size_str = ""
        else:
            block_client_max_body_size_str = Template(
                block_template_client_max_body_size
            ).substitute({"client_max_body_size": self.server.client_max_body_size})

        if self.server.support_websocket:
            block_websocket = block_template_websocket
        else:
            block_websocket = ""

        return Template(block_template_location_root_with_proxy_pass).substitute(
            {
                "block_websocket": block_websocket,
                "block_client_max_body_size": block_client_max_body_size_str,
            }
        )


class GenerateOneServerStreamD(GenerateOneServerAbc):
    def id_str(self) -> str:
        return f"stream.d:[{self.server.proxy_pass}]"

    def generate(self) -> str:
        if self.server.upstream_name and self.server.upstream_server:
            block_upstream = Template(block_template_upstream).substitute(
                {
                    "upstream_name": self.server.upstream_name,
                    "upstream_server": self.server.upstream_server,
                }
            )
        else:
            block_upstream = ""

        result = ""
        if isinstance(self.server.listen, int):
            result += Template(stream_conf_template_main_no_ssl).substitute(
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen": self.server.listen,
                    "proxy_pass": self.server.proxy_pass,
                    "block_upstream": block_upstream,
                }
            )

        if isinstance(self.server.listen_ssl, int):
            block_ssl_str = self.generate_block_ssl()
            if block_ssl_str is None:
                logger.error(f"{self.id_str()} miss [ssl_cert_domain]")
                return ""

            result += Template(stream_conf_template_main_only_ssl).substitute(
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen_ssl": self.server.listen_ssl,
                    "block_ssl": block_ssl_str,
                    "proxy_pass": self.server.proxy_pass,
                    "block_upstream": block_upstream,
                }
            )

        return result


class NginxGenerator:
    CONFIG_NGINX_TOML: str
    NGINX_CONF_DIR: str

    config: Config

    http_default_listen = {NGINX_HTTP_PORT}
    http_default_listen_ssl = {NGINX_HTTPS_PORT}

    def __init__(self, config_nginx_toml: str, nginx_conf_dir: str):
        self.CONFIG_NGINX_TOML = config_nginx_toml
        self.NGINX_CONF_DIR = nginx_conf_dir

    def __call__(self, *args, **kwargs):
        # parse nginx.toml
        try:
            with open(self.CONFIG_NGINX_TOML, "rb") as f:
                config_obj = tomllib.load(f)

        except FileNotFoundError as e:
            logger.critical(f"Open file {self.CONFIG_NGINX_TOML} failed, {e}")
            exit(1)
        except tomllib.TOMLDecodeError as e:
            logger.critical(f"Parse file {self.CONFIG_NGINX_TOML} failed, {e}")
            exit(1)

        try:
            self.config = Config.model_validate(config_obj)
        except pydantic.ValidationError as e:
            logger.critical(f"Parse file {self.CONFIG_NGINX_TOML} failed, {e}")
            exit(1)

        # parser http_d

        http_conf_content = ""
        for server in self.config.http_d:
            # http.conf
            http_conf_content += GenerateOneServerHTTPD(
                server=server, default=self.config.default
            )()

            # http_defautl.conf
            if not server.enable:
                continue

            if server.listen:
                self.http_default_listen.add(server.listen)
            if server.listen_ssl:
                self.http_default_listen_ssl.add(server.listen_ssl)

        # generate http.conf
        self.generate_conf_file(
            conf_filename=Path(self.NGINX_CONF_DIR)
            .joinpath(NGINX_HTTP_CONF)
            .as_posix(),
            conf_content=http_conf_content,
        )

        # generate http_default.conf
        self.generate_conf_file(
            conf_filename=Path(self.NGINX_CONF_DIR)
            .joinpath(NGINX_HTTP_DEFAULT_CONF)
            .as_posix(),
            conf_content=self.generate_default_conf_content(),
        )

        # generate stream.conf
        stream_conf_content = ""
        for server in self.config.stream_d:
            stream_conf_content += GenerateOneServerStreamD(
                server=server, default=self.config.default
            )()
        self.generate_conf_file(
            conf_filename=Path(self.NGINX_CONF_DIR)
            .joinpath(NGINX_STREAM_CONF)
            .as_posix(),
            conf_content=stream_conf_content,
        )

    def generate_default_conf_content(self) -> str:
        default_listen_content = ""
        for port in self.http_default_listen:
            default_listen_content += Template(
                black_template_default_listen
            ).substitute({"port": port})

        default_listen_ssl_content = ""
        for port in self.http_default_listen_ssl:
            default_listen_ssl_content += Template(
                black_template_default_listen_ssl
            ).substitute({"port": port})

        return Template(http_default_conf_template).substitute(
            {
                "default_listen": default_listen_content,
                "default_listen_ssl": default_listen_ssl_content,
            }
        )

    @staticmethod
    def generate_conf_file(conf_filename: str, conf_content: str):
        logger.info(f"Generate [{conf_filename}]...")

        try:
            with open(conf_filename, "w") as f:
                f.write(conf_content)
            logger.info(f"Generate [{conf_filename}]...DONE")
        except OSError as e:
            logger.critical(f"Generate [{conf_filename}] failed, {e}")
            exit(1)
