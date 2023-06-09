#!/bin/sh

docker container stop dnsrobocert
docker container rm dnsrobocert
docker image rm cr.h.rexzhang.com/ray1ex/dnsrobocert

docker pull python:3.11-alpine
docker build -t cr.h.rexzhang.com/ray1ex/dnsrobocert . --build-arg ENV=rex

mkdir /tmp/dnsrobocert-data
docker run -dit --restart unless-stopped \
  -u 501:20 -p 8000:8000 \
  -v ./dnsrobocert.yml:/config/dnsrobocert.yml \
  -v /tmp/dnsrobocert-data:/data \
  --name dnsrobocert cr.h.rexzhang.com/ray1ex/dnsrobocert
docker image prune -f
docker container logs -f dnsrobocert
