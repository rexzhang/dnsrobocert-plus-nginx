from logging import getLogger
from string import Template

from plush.config import HTTPD
from plush.nginx.common import GenerateOneServerConfAbc, server_block_template_upstream

logger = getLogger("plush.nginx")


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


class GenerateOneHttpServerConf(GenerateOneServerConfAbc):
    server: HTTPD

    @property
    def type(self) -> str:
        return "HttpServer"

    @property
    def label(self) -> str:
        match (
            self.server.server_name is None,
            self.server.root_path is None,
            self.server.proxy_pass is None,
        ):
            case False, False, True:
                return f"{self.type}: [{self.server.root_path}] => [{self.server.server_name}]"
            case False, True, False:
                return f"{self.type}: [{self.server.proxy_pass}] => [{self.server.server_name}]"

        return "?"

    def _generate_conf_content(self) -> str:
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
                logger.error(f"{self.label} miss [root_path] and [proxy_pass]")
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
                logger.error(f"{self.label} miss [listen] and [listen_ssl]")
                return ""

        match self.server.listen_http2, self.server.listen_ipv6:
            case True, True:
                listen = (
                    f"listen {self.server.listen}; listen [::]:{self.server.listen};"
                )
                listen_ssl = f"listen {self.server.listen_ssl} ssl; listen [::]:{self.server.listen_ssl} ssl; http2 on;"  # noqa E501

            case True, False:
                listen = f"listen {self.server.listen};"
                listen_ssl = f"listen {self.server.listen_ssl} ssl; http2 on;"

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
            block_upstream = Template(server_block_template_upstream).substitute(
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
