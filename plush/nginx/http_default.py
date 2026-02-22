from pathlib import Path

from plush.config import HttpDeafult
from plush.nginx.common import GenerateOneConfAbc
from plush.tempalte import Template

http_default_listen = [80, 443]
http_default_listen_ssl = [443]

http_default_conf_block_template_listen = """
listen {{ port }} default_server;
listen [::]:{{ port }} default_server;"""

http_default_conf_block_template_listen_ssl = """
listen {{ port }} ssl default_server;
listen [::]:{{ port }} ssl default_server;"""

http_default_conf_block_template_listen_ssl_http2_on = """
http2 on;"""

# https://serverfault.com/questions/578648/properly-setting-up-a-default-nginx-server-for-https
http_default_conf_template = """
map "" $empty {
    default "";
}

server {
    {{ default_listen }}

    server_name _;

    return 444;
}

server {
    {{ default_listen_ssl }}

    server_name _;

    ssl_ciphers aNULL;
    ssl_certificate data:$empty;
    ssl_certificate_key data:$empty;

    return 444;
}
"""


class GenerateHttpDefaultConf(GenerateOneConfAbc):
    @property
    def type(self) -> str:
        return "HttpDefault"

    @property
    def label(self) -> str:
        return self.type

    def __init__(
        self,
        http_default: HttpDeafult,
        full_path: Path,
    ):
        self._init_common(enable=True, name=full_path.name, base_path=full_path)
        self.full_path = full_path

        self.http_default_listen = http_default.http_default_listen
        self.http_default_listen_ssl = http_default.http_default_listen_ssl

    def _generate_conf_content(self) -> str:
        default_listen_content = ""
        for port in self.http_default_listen:
            default_listen_content += Template().render(
                http_default_conf_block_template_listen,
                {"port": port},
            )

        default_listen_ssl_content = ""
        for port in self.http_default_listen_ssl:
            default_listen_ssl_content += Template().render(
                http_default_conf_block_template_listen_ssl,
                {"port": port},
            )
        if default_listen_ssl_content:  # TODO: global value/constant
            default_listen_ssl_content += (
                http_default_conf_block_template_listen_ssl_http2_on
            )

        return Template().render(
            http_default_conf_template,
            {
                "default_listen": default_listen_content,
                "default_listen_ssl": default_listen_ssl_content,
            },
        )