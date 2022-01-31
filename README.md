# dnsrobocert-docker

[![Docker Pulls](https://img.shields.io/docker/pulls/ray1ex/dnsrobocert)](https://hub.docker.com/repository/docker/ray1ex/dnsrobocert)

[Github repos](https://github.com/rexzhang/dnsrobocert-docker/)

# Quick Start

## Install
```shell
docker pull ray1ex/dnsrobocert:latest
docker run -dit -v /your/dnsrobocert.yml:/etc/dnsrobocert.yml -v /your/path:/data \
  -e UID=1000 -e GID=1000 \
  --name dnsrobocert ray1ex/dnsrobocert
```

# Environment Variables

| Name      | Defaule Value              | Memo |
|-----------|----------------------------|------|
| GID       | 1000                       | -    |
| UID       | 1000                       | -    |

# More Info
- https://github.com/adferrand/dnsrobocert
- `oci` does not support python3.10
