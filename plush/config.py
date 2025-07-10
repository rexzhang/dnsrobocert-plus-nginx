import pydantic


class Default(pydantic.BaseModel):  # => Common
    ssl_cert_domain: str


class Upstream(pydantic.BaseModel):
    # 配置文件兼容 http upstream 和 stream upstream
    enable: bool = True

    name: str
    content: str


class ServerAbc(pydantic.BaseModel):
    enable: bool = True

    listen: int | None = None
    listen_ssl: int | None = None

    ssl_cert_domain: str | None = None

    upstream_name: str | None = None
    upstream_server: str | None = None


class HTTPD(ServerAbc):
    server_name: str

    listen_http2: bool = True
    listen_ipv6: bool = True

    root_path: str | None = None
    proxy_pass: str | None = None
    location: dict[str, str] = dict()

    client_max_body_size: str | None = None
    support_websocket: bool = False
    hsts: bool = False
    hsts_max_age: int = 31536000

    @property
    def name(self) -> str:
        return self.server_name


class StreamD(ServerAbc):
    comment: str = "---"

    proxy_pass: str

    @property
    def name(self) -> str:
        data = list()
        if self.listen:
            data.append(f"p{self.listen}")
        if self.listen_ssl:
            data.append(f"p{self.listen_ssl}")

        result = "_".join(data)
        if not result:
            result = "?"

        return result


class Config(pydantic.BaseModel):
    default: Default

    http_upstream: list[Upstream] = list()
    http_d: list[HTTPD]  # -> http_server

    stream_d: list[StreamD] = list()  # -> stream_server
