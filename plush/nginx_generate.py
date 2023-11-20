import builtins
import tomllib
from logging import getLogger
from pathlib import Path
from string import Template

import pydantic

logger = getLogger(__name__)

CONF_FILENAME_HTTP_D = "http.conf"
CONF_FILENAME_STREAM_D = "stream.conf"

SSL_FILE_BASE_PATH = "/data/dnsrobocert/live"

block_template_ssl = """
ssl_certificate     $ssl_path_root/fullchain.pem;
ssl_certificate_key $ssl_path_root/privkey.pem;
include /app/nginx/snippets/ssl-params.conf;
"""

block_template_client_max_body_size = """
#  Fix: 413 - Request Entity Too Large
client_max_body_size $client_max_body_size;
"""

http_d_template_main_only_http = """
server {
    server_name $server_name;
    $listen
    
    $values
    $locations
}
"""

http_d_template_main_only_https = """
server {
    server_name $server_name;
    $listen_ssl
    
    $values
    $block_ssl
    $locations
}
"""

http_d_template_main_http_and_https = """
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
    $locations
}
"""

http_d_template_location_root_with_root_path = """
    location / {
        root $$root_path;
    }"""

http_d_template_location_root_with_proxy_pass = """
    location / {
        $block_client_max_body_size

        include /app/nginx/snippets/proxy-params.conf;
        $include_websocket
        
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
    
    $values    
    
    proxy_pass $$proxy_pass;
}
"""

stream_d_template_main_only_ssl = """
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

    listen: int = None
    listen_ssl: int = None

    ssl_cert_domain: str = None


class HTTPD(ServerAbc):
    server_name: str

    listen_http2: bool = True
    listen_ipv6: bool = True

    root_path: str | None = None
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

        # return "include /app/nginx/snippets/ssl-params.conf;"
        return Template(block_template_ssl).substitute(
            {"ssl_path_root": f"{SSL_FILE_BASE_PATH}/{ssl_cert_domain}"}
        )

    @staticmethod
    def id_str() -> str:
        raise NotImplementedError

    def generate(self) -> str:
        raise NotImplementedError


class GenerateOneServerHTTPD(GenerateOneServerAbc):
    def id_str(self) -> str:
        match self.server.server_name is None, self.server.root_path is None, self.server.proxy_pass is None:
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
            locations_str += Template(http_d_template_location_custom).substitute(
                {"location_path": k, "location_content": v}
            )

        # httpd main
        match (
            isinstance(self.server.listen, int),
            isinstance(self.server.listen_ssl, int),
        ):
            case (True, False):
                main_template = Template(http_d_template_main_only_http)
            case (False, True):
                main_template = Template(http_d_template_main_only_https)
            case (True, True):
                main_template = Template(http_d_template_main_http_and_https)
            case _:
                logger.error(f"{self.id_str()} miss [listen] and [listen_ssl]")
                return ""

        match self.server.listen_http2, self.server.listen_ipv6:
            case True, True:
                listen = (
                    f"listen {self.server.listen}; listen [::]:{self.server.listen};"
                )
                listen_ssl = f"listen {self.server.listen_ssl} ssl http2; listen [::]:{self.server.listen_ssl} ssl http2;"

            case True, False:
                listen = f"listen {self.server.listen};"
                listen_ssl = f"listen {self.server.listen_ssl} ssl http2;"

            case False, True:
                listen = (
                    f"listen {self.server.listen}; listen [::]:{self.server.listen};"
                )
                listen_ssl = f"listen {self.server.listen_ssl} ssl; listen [::]:{self.server.listen_ssl} ssl;"

            case False, False:
                listen = f"listen {self.server.listen};"
                listen_ssl = f"listen {self.server.listen_ssl} ssl;"

            case _:
                raise

        result = main_template.substitute(
            {
                "values": self.generate_values_list_str(),
                "server_name": self.server.server_name,
                "listen": listen,
                "listen_ssl": listen_ssl,
                "block_ssl": self.generate_block_ssl(),
                "locations": locations_str,
            }
        )

        return result

    def _generate_location_root_with_root(self) -> str:
        return Template(http_d_template_location_root_with_root_path).substitute(
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
            include_websocket = "include /app/nginx/snippets/websocket.conf;"
        else:
            include_websocket = ""

        return Template(http_d_template_location_root_with_proxy_pass).substitute(
            {
                "include_websocket": include_websocket,
                "block_client_max_body_size": block_client_max_body_size_str,
            }
        )


class GenerateOneServerStreamD(GenerateOneServerAbc):
    def id_str(self) -> str:
        return f"stream.d:[{self.server.proxy_pass}]"

    def generate(self) -> str:
        result = ""
        if isinstance(self.server.listen, int):
            result += Template(stream_d_template_main_no_ssl).substitute(
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen": self.server.listen,
                    "proxy_pass": self.server.proxy_pass,
                }
            )

        if isinstance(self.server.listen_ssl, int):
            block_ssl_str = self.generate_block_ssl()
            if block_ssl_str is None:
                logger.error(f"{self.id_str()} miss [ssl_cert_domain]")
                return ""

            result += Template(stream_d_template_main_only_ssl).substitute(
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen_ssl": self.server.listen_ssl,
                    "block_ssl": block_ssl_str,
                    "proxy_pass": self.server.proxy_pass,
                }
            )

        return result


class NginxGenerator:
    nginx_toml: str
    http_d_dir: str
    stream_d_dir: str

    config: Config

    def __init__(self, nginx_toml: str, http_d_dir: str, stream_d_dir: str):
        self.nginx_toml = nginx_toml
        self.http_d_dir = http_d_dir
        self.stream_d_dir = stream_d_dir

    def __call__(self, *args, **kwargs):
        # parse nginx.toml
        try:
            with open(self.nginx_toml, "rb") as f:
                config_obj = tomllib.load(f)

        except FileNotFoundError as e:
            logger.critical(f"Open file {self.nginx_toml} failed, {e}")
            exit(1)
        except tomllib.TOMLDecodeError as e:
            logger.critical(f"Parse file {self.nginx_toml} failed, {e}")
            exit(1)

        try:
            self.config = Config.model_validate(config_obj)
        except pydantic.ValidationError as e:
            logger.critical(f"Parse file {self.nginx_toml} failed, {e}")
            exit(1)

        # generate http.d
        conf_content = ""
        for server in self.config.http_d:
            conf_content += GenerateOneServerHTTPD(
                server=server, default=self.config.default
            )()
        conf_filename = Path(self.http_d_dir).joinpath(CONF_FILENAME_HTTP_D).as_posix()
        self.generate_conf_file(conf_filename=conf_filename, conf_content=conf_content)

        # generate stream.d
        conf_content = ""
        for server in self.config.stream_d:
            conf_content += GenerateOneServerStreamD(
                server=server, default=self.config.default
            )()
        conf_filename = (
            Path(self.stream_d_dir).joinpath(CONF_FILENAME_STREAM_D).as_posix()
        )
        self.generate_conf_file(conf_filename=conf_filename, conf_content=conf_content)

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
