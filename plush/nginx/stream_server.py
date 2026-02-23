from logging import getLogger

from ..config import StreamServer
from ..tempalte import Template
from .common import GenerateOneServerConfAbc

logger = getLogger(__name__)
stream_conf_template_main_no_ssl = """
server {
    # {{ comment }}
    listen {{ listen }}; listen [::]:{{ listen }};

    {{ values }}

    proxy_pass {{ proxy_pass }};
}
"""

stream_conf_template_main_only_ssl = """
server {
    # {{ comment }}
    listen {{ listen_ssl }} ssl; listen [::]:{{ listen_ssl }} ssl;

    {{ values }}

    proxy_ssl on;
    {{ block_ssl }}

    proxy_pass {{ proxy_pass }};
}
"""


class GenerateOneStreamServerConf(GenerateOneServerConfAbc):
    server: StreamServer

    @property
    def type(self) -> str:
        return "StreamServer"

    @property
    def label(self) -> str:
        return f"{self.type}: [{self.server.proxy_pass}]"

    def _generate_conf_content(self) -> str:
        result = ""
        if isinstance(self.server.listen, int):
            template = Template()
            result += template.render(
                stream_conf_template_main_no_ssl,
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen": self.server.listen,
                    "proxy_pass": self.server.proxy_pass,
                },
            )

        if isinstance(self.server.listen_ssl, int):
            block_ssl_str = self.generate_block_ssl()
            if block_ssl_str is None:
                logger.error(f"{self.label} miss [ssl_cert_domain]")
                return ""

            template = Template()
            result += template.render(
                stream_conf_template_main_only_ssl,
                {
                    "comment": self.server.comment,
                    "values": self.generate_values_list_str(),
                    "listen_ssl": self.server.listen_ssl,
                    "block_ssl": block_ssl_str,
                    "proxy_pass": self.server.proxy_pass,
                },
            )

        return result
