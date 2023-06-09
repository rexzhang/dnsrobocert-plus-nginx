import tomllib
from logging import getLogger
from pathlib import Path
from string import Template

import pydantic

logger = getLogger(__name__)

HTTP_D_CONF_FILENAME = "http.conf"
STREAM_D_CONF_FILENAME = "stream.conf"

SNIPPET_PROXY_PARAMS = """
        # proxy_params
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;"""

SNIPPET_WEBSOCKET = """
"""

SNIPPET_TEMPLATE_SSL = """
    # ssl_params
    ssl_certificate     $ssl_crt_file;
    ssl_certificate_key $ssl_key_file;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;"""

SNIPPET_TEMPLATE_CLIENT_MAX_BODY_SIZE = """
        # Fix: 413 - Request Entity Too Large
        client_max_body_size $client_max_body_size;
"""

httpd_template_main_http_and_https = """
server {
    listen $listen_http;
    listen [::]:$listen_http;
    server_name $server_name;

    return 301 https://$server_name$$request_uri;
}

server {
    listen $listen_https ssl http2;
    listen [::]:$listen_https ssl http2;
    server_name $server_name;

    $ssl_params
    
    set $$upstream $upstream;

    $locations
}
"""

httpd_template_main_only_http = """
server {
    listen $listen_http;
    listen [::]:$listen_http;
    server_name $server_name;
    
    set $$upstream $upstream;
    
    $locations
}"""

httpd_template_main_only_https = """
server {
    listen $listen_https ssl http2;
    listen [::]:$listen_https ssl http2;
    server_name $server_name;

    set $$upstream $upstream;

    $ssl_params
    $locations
}"""

httpd_template_location_default = """
    location / {
        $proxy_params
        $client_max_body_size

        proxy_pass $$upstream;
    }"""

httpd_template_location_custom = """
    location $location_path {
        $location_content
    }"""


class Default(pydantic.BaseModel):
    ssl_crt_file: str
    ssl_key_file: str


class HTTPD(pydantic.BaseModel):
    server_name: str

    listen_http: int = None
    listen_https: int = None

    ssl_crt_file: str = None
    ssl_key_file: str = None
    upstream: str

    location: dict[str, str] = dict()
    client_max_body_size: str = None


class Config(pydantic.BaseModel):
    default: Default
    httpd: list[HTTPD]


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
        http_d_conf_filename = (
            Path(self.http_d_dir).joinpath(HTTP_D_CONF_FILENAME).as_posix()
        )
        logger.info(f"Generate httpd file:[{http_d_conf_filename}]...")
        httpd_conf_str = str()
        for httpd in self.config.httpd:
            httpd_conf_str += self._generate_one_httpd(httpd)

        try:
            with open(http_d_conf_filename, "w") as f:
                f.write(httpd_conf_str)
            logger.info(f"Generate httpd file:[{http_d_conf_filename}]...DONE")
        except IOError as e:
            logger.critical(f"Generate httpd file:[{http_d_conf_filename}] failed, {e}")
            exit(1)

    def _generate_ssl_snippet(self, ssl_crt_file: str, ssl_key_file: str) -> str | None:
        if ssl_crt_file is None or ssl_key_file is None:
            ssl_crt_file = self.config.default.ssl_crt_file
            ssl_key_file = self.config.default.ssl_key_file

        if ssl_crt_file is None or ssl_key_file is None:
            # default is None
            return None

        return Template(SNIPPET_TEMPLATE_SSL).substitute(
            {
                "ssl_crt_file": f"{ssl_crt_file}",
                "ssl_key_file": f"{ssl_key_file}",
            }
        )

    def _generate_one_httpd(self, httpd: HTTPD) -> str:
        httpd_str = str()

        # httpd ssl
        if not isinstance(httpd.listen_https, int):
            ssl_params_str = ""
        else:
            ssl_params_str = self._generate_ssl_snippet(
                httpd.ssl_crt_file, httpd.ssl_key_file
            )
            if ssl_params_str is None:
                logger.error(
                    f"httpd:[{httpd.server_name}] miss [ssl_crt_file] and [ssl_key_file]"
                )
                return ""

        # httpd location
        locations_str = str()
        if "/" not in httpd.location:
            if httpd.client_max_body_size is None:
                client_max_body_size_str = ""
            else:
                client_max_body_size_str = Template(
                    SNIPPET_TEMPLATE_CLIENT_MAX_BODY_SIZE
                ).substitute({"client_max_body_size": httpd.client_max_body_size})

            locations_str += Template(httpd_template_location_default).substitute(
                {
                    "proxy_params": SNIPPET_PROXY_PARAMS,
                    "client_max_body_size": client_max_body_size_str,
                }
            )

        for k, v in httpd.location.items():
            locations_str += Template(httpd_template_location_custom).substitute(
                {"location_path": k, "location_content": v}
            )

        # httpd main
        main_template = None
        match (isinstance(httpd.listen_http, int), isinstance(httpd.listen_https, int)):
            case (False, False):
                logger.error(
                    f"httpd:[{httpd.server_name}] miss [listen_http] and [listen_https]"
                )
                return ""
            case (True, False):
                main_template = Template(httpd_template_main_only_http)
            case (False, True):
                main_template = Template(httpd_template_main_only_https)
            case (True, True):
                main_template = Template(httpd_template_main_http_and_https)

        httpd_str += main_template.substitute(
            {
                "server_name": httpd.server_name,
                "listen_http": httpd.listen_http,
                "listen_https": httpd.listen_https,
                "ssl_params": ssl_params_str,
                "upstream": httpd.upstream,
                "locations": locations_str,
            }
        )
        return httpd_str
