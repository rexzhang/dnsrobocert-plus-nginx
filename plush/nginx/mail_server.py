from logging import getLogger
from string import Template


from ..tempalte import Template
from ..constants import NginxMailServerType

from .common import GenerateOneServerConfAbc
from ..config import MailServer


mail_conf_template_ssl = """
server {
    listen     {{ server.port }} ssl;
    protocol   smtp;
    proxy_protocol on;
    xclient    on;

    {{ block_ssl }}

    smtp_auth login plain;
    auth_http {{ server.auth_http }};
}
"""

mail_conf_template_starttls = """
server {
    listen    {{ server.port }};
    protocol  smtp;
    proxy_protocol on;
    xclient    on;

    starttls  on;
    {{ block_ssl }}

    smtp_auth login plain;
    auth_http {{ server.auth_http }};
}
"""


class GenerateOneMailServerConf(GenerateOneServerConfAbc):
    server: MailServer

    @property
    def type(self) -> str:
        return "MailServer"

    @property
    def label(self) -> str:
        return f"{self.type}: [{self.server.port}] => [{self.server.auth_http}]"

    def _generate_conf_content(self) -> str:
        match self.server.type:
            case NginxMailServerType.SSL:
                template_name = mail_conf_template_ssl
            case NginxMailServerType.STARTTLS:
                template_name = mail_conf_template_starttls
            case _:
                raise

        template = Template()
        return template.render(
            template_name,
            {"server": self.server, "block_ssl": self.generate_block_ssl()},
        )
