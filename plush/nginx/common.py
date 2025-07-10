import builtins
from logging import getLogger
from pathlib import Path
from string import Template

from plush.config import HTTPD, Default, ServerAbc, StreamD
from plush.constants import DNSROBOCERT_SSL_FILE_DIR

logger = getLogger("plush.nginx")


class GenerateOneConfAbc:
    # 输入
    name: str
    content: str

    enable: bool = True

    # 内部数据
    _values: dict = dict()

    # 输出信息
    file_name: str
    base_path: Path
    full_path: Path

    def __init__(self):
        raise NotImplementedError

    def _init_common(self, name: str, enable: bool, base_path: Path):
        self.name = name

        self.enable = enable

        self.file_name = f"{name}.conf"
        self.base_path = base_path
        self.full_path = self.base_path.joinpath(self.file_name)

    @property
    def type(self) -> str:
        raise NotImplementedError

    @property
    def label(self) -> str:
        f"{self.type}:[{self.label}]"
        raise NotImplementedError

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

    def generate(self):
        self.content = self._generate_conf_content()
        self._generate_conf_file()

    def _generate_conf_content(self) -> str:
        raise NotImplementedError

    def _generate_conf_file(self):
        message_base = f" {self.label} >> {self.file_name}"

        if not self.enable:
            logger.warning(f"{message_base} Skip(Disabled)!")
            return

        logger.info(f"{message_base} Generate...")
        try:
            with open(self.full_path, "w") as f:
                f.write(self.content)

            logger.info(f"{message_base} Generate...DONE")

        except OSError as e:
            logger.critical(f"{message_base} Generate...failed, {e}")
            exit(1)


server_block_template_upstream = """
# upstream server define
upstream $upstream_name {
    server $upstream_server;
}"""

server_block_template_ssl = """
# SSL certificate
ssl_certificate     $ssl_path_root/fullchain.pem;
ssl_certificate_key $ssl_path_root/privkey.pem;
include /app/nginx/snippets/ssl-params.conf;"""


class GenerateOneServerConfAbc(GenerateOneConfAbc):

    server: ServerAbc
    default: Default

    def __init__(self, server: HTTPD | StreamD, default: Default, base_path: Path):
        self._init_common(name=server.name, enable=server.enable, base_path=base_path)

        self.server = server
        self.default = default

        if server.proxy_pass:
            self.update_value(k="proxy_pass", v=server.proxy_pass)

    def generate_block_ssl(self) -> str:
        if self.server.ssl_cert_domain is None:
            ssl_cert_domain = self.default.ssl_cert_domain
        else:
            ssl_cert_domain = self.server.ssl_cert_domain

        if ssl_cert_domain is None:
            # default is None
            return ""

        return Template(server_block_template_ssl).substitute(
            {
                "ssl_path_root": Path(DNSROBOCERT_SSL_FILE_DIR)
                .joinpath(ssl_cert_domain)
                .as_posix()
            }
        )
