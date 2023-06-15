# dnsrobocert-plus-nginx[WIP]

[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/dnsrobocert-plus-nginx)](https://hub.docker.com/repository/docker/ray1ex/dnsrobocert-plus-nginx)

[Github repos](https://github.com/rexzhang/dnsrobocert-plus-nginx/)

- simple
- one container
- none-root user
- none-SQL
- for self-hosted

# Quick Start

## Install

```shell
docker pull ray1ex/dnsrobocert-plus-nginx:latest
docker run -dit --restart unless-stopped \ 
  -u 1000:1000 -p 80:10080 -p 443:10443 \
  -v /your/path/config:/config \
  -v /your/path/data:/data \
  -v /your/path/log:/log \
  --name dnsrobocert-plus-nginx ray1ex/dnsrobocert-plus-nginx
```

# Config Example

`/your/path/config/dnsrobocert.yml`

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
    deploy_hook: nginx -s reload
```

`/your/path/config/nginx.toml`

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
root = "root /mnt/www/www2.example.com"
```

# More Info

- https://github.com/adferrand/dnsrobocert

# debug

```shell
python -m plush generate --nginx-toml nginx.toml --http-d-dir /tmp --stream-d-dir /tmp
```