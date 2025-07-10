from logging import getLogger
from string import Template

from plush.config import StreamD
from plush.nginx.common import GenerateOneServerConfAbc, server_block_template_upstream

logger = getLogger(__name__)
stream_conf_template_main_no_ssl = """
$block_upstream
server {
    # $comment
    listen $listen; listen [::]:$listen;

    $values

    proxy_pass $$proxy_pass;
}
"""

stream_conf_template_main_only_ssl = """
$block_upstream
server {
    # $comment
    listen $listen_ssl ssl; listen [::]:$listen_ssl ssl;

    $values

    proxy_ssl on;
    $block_ssl

    proxy_pass $$proxy_pass;
}
"""


class GenerateOneStreamServerConf(GenerateOneServerConfAbc):
    server: StreamD

    @property
    def type(self) -> str:
        return "StreamServer"

    @property
    def label(self) -> str:
        return f"{self.type}: [{self.server.proxy_pass}]"

    def _generate_conf_content(self) -> str:
        if self.server.upstream_name and self.server.upstream_server:
            block_upstream = Template(server_block_template_upstream).substitute(
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
                logger.error(f"{self.label} miss [ssl_cert_domain]")
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
