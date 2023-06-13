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
    listen $listen;
    listen [::]:$listen;
    server_name $server_name;
    
    set $$proxy_pass $proxy_pass;
    
    $locations
}"""

http_d_template_main_only_https = """
server {
    listen $listen_ssl ssl http2;
    listen [::]:$listen_ssl ssl http2;
    server_name $server_name;

    set $$proxy_pass $proxy_pass;

    $ssl_params
    $locations
}"""

http_d_template_main_http_and_https = """
server {
    listen $listen;
    listen [::]:$listen;
    server_name $server_name;

    return 301 https://$server_name$$request_uri;
}

server {
    listen $listen_ssl ssl http2;
    listen [::]:$listen_ssl ssl http2;
    server_name $server_name;

    $ssl_params

    set $$proxy_pass $proxy_pass;

    $locations
}
"""

http_d_template_location_default = """
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

    proxy_pass: str


class HTTPD(ServerAbc):
    server_name: str

    location: dict[str, str] = dict()
    client_max_body_size: str = None
    support_websocket: bool = False


class StreamD(ServerAbc):
    comment: str = "---"


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
        logger.info(f"Generate http.d file:[{http_d_conf_filename}]...")
        http_d_conf_str = ""
        for http_d in self.config.http_d:
            if http_d.enable:
                http_d_conf_str += self._generate_one_http_d(http_d)
                logger.info(
                    f"Generate http.d:[{http_d.proxy_pass}] >> [{http_d.server_name}]"
                )
            else:
                logger.info(
                    f"Skip http.d:[{http_d.proxy_pass}] >> [{http_d.server_name}]"
                )

        try:
            with open(http_d_conf_filename, "w") as f:
                f.write(http_d_conf_str)
            logger.info(f"Generate http.d file:[{http_d_conf_filename}]...DONE")
        except OSError as e:
            logger.critical(
                f"Generate http.d file:[{http_d_conf_filename}] failed, {e}"
            )
            exit(1)

        # stream.d
        stream_d_conf_filename = (
            Path(self.stream_d_dir).joinpath(STREAM_D_CONF_FILENAME).as_posix()
        )
        logger.info(f"Generate stream.d file:[{stream_d_conf_filename}]...")
        stream_d_conf_str = ""
        for stream_d in self.config.stream_d:
            if stream_d.enable:
                stream_d_conf_str += self._generate_one_stream_d(stream_d)
                logger.info(f"Generate http.d:[{stream_d.proxy_pass}]")
            else:
                logger.info(f"Skip http.d:[{stream_d.proxy_pass}]")

        try:
            with open(stream_d_conf_filename, "w") as f:
                f.write(stream_d_conf_str)
            logger.info(f"Generate stream.d file:[{stream_d_conf_filename}]...DONE")
        except OSError as e:
            logger.critical(
                f"Generate stream.d file:[{stream_d_conf_filename}] failed, {e}"
            )
            exit(1)

    def _generate_ssl_snippet(self, ssl_cert_domain: str) -> str | None:
        if ssl_cert_domain is None:
            ssl_cert_domain = self.config.default.ssl_cert_domain

        if ssl_cert_domain is None:
            # default is None
            return None

        return Template(SNIPPET_TEMPLATE_SSL).substitute(
            {
                "SSL_FILE_BASE_PATH": f"{SSL_FILE_BASE_PATH}",
                "ssl_cert_domain": f"{ssl_cert_domain}",
            }
        )

    def _generate_one_http_d(self, http_d: HTTPD) -> str:
        http_d_str = ""

        # httpd ssl
        if not isinstance(http_d.listen_ssl, int):
            ssl_params_str = ""
        else:
            ssl_params_str = self._generate_ssl_snippet(http_d.ssl_cert_domain)
            if ssl_params_str is None:
                logger.error(f"http.d:[{http_d.server_name}] miss [ssl_cert_domain]")
                return ""

        # httpd location
        locations_str = ""
        if "/" not in http_d.location:
            # create from default template
            if http_d.client_max_body_size is None:
                client_max_body_size_str = ""
            else:
                client_max_body_size_str = Template(
                    SNIPPET_TEMPLATE_CLIENT_MAX_BODY_SIZE
                ).substitute({"client_max_body_size": http_d.client_max_body_size})

            if http_d.support_websocket:
                support_websocket = SNIPPET_WEBSOCKET
            else:
                support_websocket = ""

            locations_str += Template(http_d_template_location_default).substitute(
                {
                    "proxy_params": SNIPPET_PROXY_PARAMS,
                    "client_max_body_size": client_max_body_size_str,
                    "support_websocket": support_websocket,
                }
            )

        for k, v in http_d.location.items():
            locations_str += Template(http_d_template_location_custom).substitute(
                {"location_path": k, "location_content": v}
            )

        # httpd main
        main_template = None
        match (isinstance(http_d.listen, int), isinstance(http_d.listen_ssl, int)):
            case (False, False):
                logger.error(
                    f"http.d:[{http_d.server_name}] miss [listen] and [listen_ssl]"
                )
                return ""
            case (True, False):
                main_template = Template(http_d_template_main_only_http)
            case (False, True):
                main_template = Template(http_d_template_main_only_https)
            case (True, True):
                main_template = Template(http_d_template_main_http_and_https)

        http_d_str += main_template.substitute(
            {
                "server_name": http_d.server_name,
                "listen": http_d.listen,
                "listen_ssl": http_d.listen_ssl,
                "ssl_params": ssl_params_str,
                "proxy_pass": http_d.proxy_pass,
                "locations": locations_str,
            }
        )
        return http_d_str

    def _generate_one_stream_d(self, stream_d: StreamD) -> str:
        stream_d_str = ""
        if isinstance(stream_d.listen, int):
            stream_d_str += Template(stream_d_template_main_no_ssl).substitute(
                {
                    "comment": stream_d.comment,
                    "listen": stream_d.listen,
                    "proxy_pass": stream_d.proxy_pass,
                }
            )

        if isinstance(stream_d.listen_ssl, int):
            ssl_params_str = self._generate_ssl_snippet(stream_d.ssl_cert_domain)
            if ssl_params_str is None:
                logger.error(f"stream.s:[{stream_d.listen_ssl}] miss [ssl_cert_domain]")
                return ""

            stream_d_str += Template(stream_d_template_main_only_ssl).substitute(
                {
                    "comment": stream_d.comment,
                    "listen_ssl": stream_d.listen_ssl,
                    "ssl_params": ssl_params_str,
                    "proxy_pass": stream_d.proxy_pass,
                }
            )
        return stream_d_str
