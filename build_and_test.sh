#!/bin/sh

docker container stop dnsrobocert
docker container rm dnsrobocert
#docker image rm cr.h.rexzhang.com/ray1ex/dnsrobocert

docker pull python:3.11-alpine
docker build -t cr.h.rexzhang.com/ray1ex/dnsrobocert . --build-arg ENV=rex
docker image prune -f

mkdir /tmp/dnsrobocert-data
docker run -dit --restart unless-stopped \
  -u 501:20 -p 8000:8000 -p 443:4430 \
  -v .:/config \
  -v /tmp:/data \
  --name dnsrobocert cr.h.rexzhang.com/ray1ex/dnsrobocert
docker container logs -f dnsrobocert
