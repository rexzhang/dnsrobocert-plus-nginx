# dnsrobocert-plus-nginx

[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/dnsrobocert)](https://hub.docker.com/repository/docker/ray1ex/dnsrobocert)

[Github repos](https://github.com/rexzhang/dnsrobocert-docker/)

- simple
- one container
- none-root user
- none-SQL
- for self-hosted

# Quick Start

## Install
```shell
docker pull ray1ex/dnsrobocert:latest
docker run -dit --restart unless-stopped \ 
  -e UID=1000 -e GID=1000 \
  -v /your/path/config.yml:/etc/dnsrobocert.yml \
  -v /your/path/data:/data \
  -v /your/path/nginx:/nginx \
  --name dnsrobocert ray1ex/dnsrobocert
```

# Environment Variables

| Name | Defaule Value |
|------|---------------|
| GID  | 1000          |
| UID  | 1000          |

# Deploy Hook Example for Nginx

`config.yml`
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
  deploy_hook: /data/export-to-nginx.sh
```

`/data/export-to-nginx.sh`
```shell
#!/bin/sh

/bin/cp -f /data/archive/your.domain.com/privkey1.pem /nginx/your.domain.com.key
/bin/cp -f /data/archive/your.domain.com/fullchain1.pem /nginx/your.domain.com.crt
```

# More Info
- https://github.com/adferrand/dnsrobocert
- `oci` does not support python3.10
