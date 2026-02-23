# dnsrobocert-plus-nginx[WIP]

![Docker Image Version (tag latest semver)](https://img.shields.io/docker/v/ray1ex/dnsrobocert-plus-nginx/latest)
[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/dnsrobocert-plus-nginx)](https://hub.docker.com/r/ray1ex/dnsrobocert-plus-nginx/tags)

- simple
- one container
- non-root
- non-SQL
- for self-hosted

## Quick Start

### Install

```shell
docker pull ray1ex/dnsrobocert-plus-nginx:latest
docker run -dit --restart unless-stopped \
  -u 1000:1000 \
  -p 80:10080 -p 443:10443 -p 22:10022 \
  -v /your/path/config:/config \
  -v /your/path/data:/data \
  -v /your/path/logs:/logs \
  --name dnsrobocert-plus-nginx ray1ex/dnsrobocert-plus-nginx
```

## Config Example

### `/your/path/config/dnsrobocert.yml`

```yaml
draft: false
acme:
  email_account: your@email.com
  staging: false
profiles:
  - name: cloudflare
    provider: cloudflare
    provider_options:
      auth_token: token-token
    sleep_time: 45
    max_checks: 5
certificates:
  - name: example.com
  domains:
      - example.com
      - "*.example.com"
    profile: cloudflare
```

Ref：

- [DNSroboCert’s provider options page](https://dnsrobocert.readthedocs.io/en/latest/configuration_reference.html)
- [Lexicon’s provider options page](https://dns-lexicon.readthedocs.io/en/latest/providers_options.html)

### `/your/path/config/nginx.toml`

```toml
[ssl_cert]
default_ssl_cert_domain = "example.com"

[[http_server]]
server_name = "www.example.com"
listen = 10080
listen_ssl = 10443
proxy_pass = "http://172.17.0.1:8000"

[[http_server]]
server_name = "www2.example.com"
listen = 10080
listen_ssl = 10443
root_path = "root /mnt/www/www2.example.com"

[[http_upstream]]
name = "upstream_websocket"
content = """
    least_conn;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
"""

[[http_server]]
server_name = "ws.example.com"
listen = 10080
proxy_pass = "upstream_websocket"
support_websocket = true

[[stream_server]]
comment = "ssh"
listen = 10022
proxy_pass = "192.168.1.1:22"

[[mail_server]]
type = "ssl"
port = 465
auth_http = "localhost:8000/api/smtpd/auth"
```

more examples please visit `examples/nginx.toml`

## NGINX config dir

| part            | dir                             |
| --------------- | ------------------------------- |
| http_upstream   | `/data/nginx/http_upstream.d`   |
| http_server     | `/data/nginx/http_server.d`     |
| stream_upstream | `/data/nginx/stream_upstream.d` |
| stream_server   | `/data/nginx/stream_server.d`   |
| mail_server     | `/data/nginx/mail_server.d`     |

## FAQ

## Why is `listen_http = false` set, NGINX is still response http2

Please `http2` turn off all services under the same port, which is a feature of NGINX.

## More Info

- <https://github.com/adferrand/dnsrobocert>

## debug

### `nginx.toml` Parser

```shell
python -m plush generate --config-nginx-toml examples/nginx.toml
```

### Test logrotate

```shell
logrotate --debug /data/logrotate.conf
```

## Memo

- 配置信息规划
  - nginx 配置复杂,使用一个统一的 nginx.toml 来管理所有配置信息
  - 其他应用的优先使用环境变量,未来数量过多后整合到 plush.toml
  - 一旦有了 plush.toml, 就考虑将 nginx.toml 也整合进去
- 文件路径规划
  - 如何可能,容器执行过程中产生的除了日志以外的其他文件都放在 /data
  - 因为权限原因,或者容器重启后需要丢弃的放 /tmp
- 代码中默认值存放规划
  - 环境变量调整的 deploy_stage.py
  - 配置文件/命令行参数调整的 constans.py

## TODO

- 统一日志输出
- nginx 启动前尝试验证配置文件
