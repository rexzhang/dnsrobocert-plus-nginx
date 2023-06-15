import tomllib
from logging import getLogger
from pathlib import Path
from string import Template

import pydantic

logger = getLogger(__name__)

HTTP_D_CONF_FILENAME = "http.conf"
STREAM_D_CONF_FILENAME = "stream.conf"

SSL_FILE_BASE_PATH = "/data/dnsrobocert/live"

SNIPPET_PROXY_PARAMS = """
        # proxy_params
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;"""

SNIPPET_WEBSOCKET = """
        # The Upgrade and Connection headers are used to establish
        # a WebSockets connection.
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
"""

SNIPPET_TEMPLATE_SSL = """
    # ssl_params
    ssl_certificate     $SSL_FILE_BASE_PATH/$ssl_cert_domain/fullchain.pem;
    ssl_certificate_key $SSL_FILE_BASE_PATH/$ssl_cert_domain/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;"""

SNIPPET_TEMPLATE_CLIENT_MAX_BODY_SIZE = """
        # Fix: 413 - Request Entity Too Large
        client_max_body_size $client_max_body_size;
"""

http_d_template_main_only_http = """
server {
    $listen
    server_name $server_name;
    
    # root_or_proxy_pass
    $root_or_proxy_pass
    $locations
}"""

http_d_template_main_only_https = """
server {
    $listen_ssl
    server_name $server_name;

    $ssl_params

    # root_or_proxy_pass
    $root_or_proxy_pass
    $locations
}"""

http_d_template_main_http_and_https = """
server {
    $listen
    server_name $server_name;

    return 301 https://$server_name$$request_uri;
}

server {
    $listen_ssl
    server_name $server_name;

    $ssl_params

    # root_or_proxy_pass
    $root_or_proxy_pass
    $locations
}
"""
http_d_template_location_default_with_root = """
    location / {
    }
"""
http_d_template_location_default_with_proxy_pass = """
    location / {
        $client_max_body_size
        $proxy_params
        $support_websocket
        
        proxy_pass $$proxy_pass;
    }"""

http_d_template_location_custom = """
    location $location_path {
        $location_content
    }"""

stream_d_template_main_no_ssl = """
server {
    # $comment
    listen $listen;
    
    proxy_pass $proxy_pass;
}"""

stream_d_template_main_only_ssl = """
server {
    # $comment
    listen $listen_ssl ssl;

    proxy_ssl on;
    $ssl_params

    proxy_pass $proxy_pass;
}"""


class Default(pydantic.BaseModel):
    ssl_cert_domain: str


class ServerAbc(pydantic.BaseModel):
    enable: bool = True

    listen: int = None
    listen_ssl: int = None

    ssl_cert_domain: str = None


class HTTPD(ServerAbc):
    server_name: str

    listen_http2: bool = True
    listen_ipv6: bool = True

    root: str | None = None
    proxy_pass: str | None = None

    location: dict[str, str] = dict()
    client_max_body_size: str | None = None
    support_websocket: bool = False


class StreamD(ServerAbc):
    comment: str = "---"

    proxy_pass: str


class Config(pydantic.BaseModel):
    default: Default
    http_d: list[HTTPD]
    stream_d: list[StreamD] = list()


class NginxGenerator:
    config: Config
    http_d_dir: str
    stream_d_dir: str

    def __init__(self, nginx_toml: str, http_d_dir: str, stream_d_dir: str):
        try:
            with open(nginx_toml, "rb") as f:
                config_obj = tomllib.load(f)

        except FileNotFoundError as e:
            logger.critical(f"Open file {nginx_toml} failed, {e}")
            exit(1)
        except tomllib.TOMLDecodeError as e:
            logger.critical(f"Parse file {nginx_toml} failed, {e}")
            exit(1)

        try:
            self.config = pydantic.parse_obj_as(Config, config_obj)
        except pydantic.error_wrappers.ValidationError as e:
            logger.critical(f"Parse file {nginx_toml} failed, {e}")
            exit(1)

        self.http_d_dir = http_d_dir
        self.stream_d_dir = stream_d_dir

    def __call__(self, *args, **kwargs):
        # http.d
        http_d_conf_filename = (
            Path(self.http_d_dir).joinpath(HTTP_D_CONF_FILENAME).as_posix()
        )
        ServerGeneratorHTTPD(
            default=self.config.default,
            servers=self.config.http_d,
            conf_filename=http_d_conf_filename,
        )()

        # stream.d
        stream_d_conf_filename = (
            Path(self.stream_d_dir).joinpath(STREAM_D_CONF_FILENAME).as_posix()
        )
        ServerGeneratorStreamD(
            default=self.config.default,
            servers=self.config.stream_d,
            conf_filename=stream_d_conf_filename,
        )()


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

    @staticmethod
    def _id_str(server: HTTPD | StreamD) -> str:
        raise NotImplementedError

    def _generate_one_server(self, server: HTTPD | StreamD) -> str:
        raise NotImplementedError

    def _generate_ssl_snippet(self, ssl_cert_domain: str) -> str | None:
        if ssl_cert_domain is None:
            ssl_cert_domain = self.default.ssl_cert_domain

        if ssl_cert_domain is None:
            # default is None
            return None

        return Template(SNIPPET_TEMPLATE_SSL).substitute(
            {
                "SSL_FILE_BASE_PATH": f"{SSL_FILE_BASE_PATH}",
                "ssl_cert_domain": f"{ssl_cert_domain}",
            }
        )


class ServerGeneratorHTTPD(ServerGeneratorAbc):
    @staticmethod
    def _id_str(server: HTTPD | StreamD) -> str:
        match server.server_name is None, server.root is None, server.proxy_pass is None:
            case False, False, True:
                return f"http.d: [{server.root}] >> [{server.server_name}]"
            case False, True, False:
                return f"http.d: [{server.proxy_pass}] >> [{server.server_name}]"

        return "?"

    def _generate_one_server(self, server: HTTPD | StreamD) -> str:
        if not server.enable:
            logger.info(f"Skip {self._id_str(server)}")
            return ""  # TODO

        # httpd ssl
        if not isinstance(server.listen_ssl, int):
            ssl_params_str = ""
        else:
            ssl_params_str = self._generate_ssl_snippet(server.ssl_cert_domain)
            if ssl_params_str is None:
                logger.error(f"{self._id_str(server)} miss [ssl_cert_domain]")
                return ""

        # httpd location
        locations_str = ""
        if "/" not in server.location:
            # create from default template
            if isinstance(server.root, str):
                locations_str = self._generate_location_root_with_root()
            elif isinstance(server.proxy_pass, str):
                locations_str = self._generate_location_root_with_proxy_pass(server)
            else:
                logger.error(f"{self._id_str(server)} miss [root] and [proxy_pass]")
                return ""

        for k, v in server.location.items():
            locations_str += Template(http_d_template_location_custom).substitute(
                {"location_path": k, "location_content": v}
            )

        # httpd main
        match (
            isinstance(server.listen, int),
            isinstance(server.listen_ssl, int),
        ):
            case (True, False):
                main_template = Template(http_d_template_main_only_http)
            case (False, True):
                main_template = Template(http_d_template_main_only_https)
            case (True, True):
                main_template = Template(http_d_template_main_http_and_https)
            case _:
                logger.error(f"{self._id_str(server)} miss [listen] and [listen_ssl]")
                return ""

        match server.listen_http2, server.listen_ipv6:
            case True, True:
                listen = f"listen {server.listen}; listen [::]:{server.listen};"
                listen_ssl = f"listen {server.listen_ssl} ssl http2; listen [::]:{server.listen_ssl} ssl http2;"

            case True, False:
                listen = f"listen {server.listen};"
                listen_ssl = f"listen {server.listen_ssl} ssl http2;"

            case False, True:
                listen = f"listen {server.listen}; listen [::]:{server.listen};"
                listen_ssl = f"listen {server.listen_ssl} ssl; listen [::]:{server.listen_ssl} ssl;"

            case False, False:
                listen = f"listen {server.listen};"
                listen_ssl = f"listen {server.listen_ssl} ssl;"

            case _:
                raise

        if server.root:
            root_or_proxy_pass = f"root {server.root};"
        elif server.proxy_pass:
            root_or_proxy_pass = f"set $proxy_pass {server.proxy_pass};"
        else:
            logger.error(f"{self._id_str(server)} miss [listen] and [listen_ssl]")
            return ""

        result = main_template.substitute(
            {
                "server_name": server.server_name,
                "listen": listen,
                "listen_ssl": listen_ssl,
                "ssl_params": ssl_params_str,
                "root_or_proxy_pass": root_or_proxy_pass,
                "locations": locations_str,
            }
        )

        logger.info(f"Generate {self._id_str(server)}")
        return result

    @staticmethod
    def _generate_location_root_with_root() -> str:
        return ""

    @staticmethod
    def _generate_location_root_with_proxy_pass(server: HTTPD | StreamD) -> str:
        if server.client_max_body_size is None:
            client_max_body_size_str = ""
        else:
            client_max_body_size_str = Template(
                SNIPPET_TEMPLATE_CLIENT_MAX_BODY_SIZE
            ).substitute({"client_max_body_size": server.client_max_body_size})

        if server.support_websocket:
            support_websocket = SNIPPET_WEBSOCKET
        else:
            support_websocket = ""

        return Template(http_d_template_location_default_with_proxy_pass).substitute(
            {
                "proxy_params": SNIPPET_PROXY_PARAMS,
                "client_max_body_size": client_max_body_size_str,
                "support_websocket": support_websocket,
            }
        )


class ServerGeneratorStreamD(ServerGeneratorAbc):
    @staticmethod
    def _id_str(server: HTTPD | StreamD) -> str:
        return f"stream.d:[{server.proxy_pass}]"

    def _generate_one_server(self, server: HTTPD | StreamD) -> str:
        if not server.enable:
            logger.info(f"Skip {self._id_str(server)}")

        result = ""
        if isinstance(server.listen, int):
            result += Template(stream_d_template_main_no_ssl).substitute(
                {
                    "comment": server.comment,
                    "listen": server.listen,
                    "proxy_pass": server.proxy_pass,
                }
            )

        if isinstance(server.listen_ssl, int):
            ssl_params_str = self._generate_ssl_snippet(server.ssl_cert_domain)
            if ssl_params_str is None:
                logger.error(f"{self._id_str(server)} miss [ssl_cert_domain]")
                return ""

            result += Template(stream_d_template_main_only_ssl).substitute(
                {
                    "comment": server.comment,
                    "listen_ssl": server.listen_ssl,
                    "ssl_params": ssl_params_str,
                    "proxy_pass": server.proxy_pass,
                }
            )

        logger.info(f"Generate {self._id_str(server)}")
        return result
