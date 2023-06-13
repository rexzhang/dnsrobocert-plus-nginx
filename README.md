# dnsrobocert-plus-nginx

[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/dnsrobocert)](https://hub.docker.com/repository/docker/ray1ex/dnsrobocert-plus-nginx)

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
  -u 1000:1000 -p 80:10080 -p 10443 \
  -v /your/path/config:/config \
  -v /your/path/data:/data \
  --name dnsrobocert-plus-nginx ray1ex/dnsrobocert-plus-nginx
```

# Deploy Hook Example for Nginx

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
      - your.domain.com
    profile: cloudflare
```

`/your/path/config/nginx.toml`

```toml
[[http_d]]
server_name = "www.example.com"
listen = 10080
listen_ssl = 10443
upstream = "http://172.17.0.1:8000"
```

# More Info

- https://github.com/adferrand/dnsrobocert
