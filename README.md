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
  - domains:
      - example.com
      - "*.example.com"
    profile: cloudflare
```

Ref：

- [DNSroboCert’s provider options page](https://dnsrobocert.readthedocs.io/en/latest/configuration_reference.html)
- [Lexicon’s provider options page](https://dns-lexicon.readthedocs.io/en/latest/providers_options.html)

### `/your/path/config/nginx.toml`

```toml
[default]
ssl_cert_domain = "example.com"

[[http_d]]
server_name = "www.example.com"
listen = 10080
listen_ssl = 10443
proxy_pass = "http://172.17.0.1:8000"

[[http_d]]
server_name = "www2.example.com"
listen = 10080
listen_ssl = 10443
root_path = "root /mnt/www/www2.example.com"

[[stream_d]]
comment = "ssh"
listen = 10022
proxy_pass = "192.168.1.1:22"
```

## FAQ

## Why is `listen_http = false` set, NGINX is still response http2

Please `http2` turn off all services under the same port, which is a feature of NGINX.

## More Info

- <https://github.com/adferrand/dnsrobocert>

## debug

```shell
python -m plush generate --nginx-toml nginx.toml --http-d-dir /tmp --stream-d-dir /tmp
```

## TODO

- 统一日志输出
- 自动重新装载nginx
