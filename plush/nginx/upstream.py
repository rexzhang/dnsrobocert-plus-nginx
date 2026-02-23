from pathlib import Path

from plush.config import Upstream
from plush.nginx.common import GenerateOneConfAbc
from plush.tempalte import Template

upstream_conf_tempalte = """upstream {{ upstream_name }} {
    {{ upstream_content }}
}"""


class GenerateOneUpstreamConf(GenerateOneConfAbc):
    @property
    def type(self) -> str:
        return "Upstream"

    @property
    def label(self) -> str:
        return self.name

    def __init__(self, upstream: Upstream, base_path: Path):
        self._init_common(
            enable=upstream.enable, name=upstream.name, base_path=base_path
        )

        self.upstream = upstream

    def _generate_conf_content(self) -> str:
        return Template().render(
            upstream_conf_tempalte,
            {
                "upstream_name": self.upstream.name,
                "upstream_content": self.upstream.content,
            },
        )
