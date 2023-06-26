#!/bin/zsh

docker container stop dnsrobocert-plus-nginx
docker container rm dnsrobocert-plus-nginx

docker pull python:3.11-alpine
docker build -t cr.h.rexzhang.com/ray1ex/dnsrobocert-plus-nginx . --build-arg ENV=rex
read -r -s -k '?Press any key to continue, push docker image...'
echo "pushing..."
docker push cr.h.rexzhang.com/ray1ex/dnsrobocert-plus-nginx

read -r -s -k '?Press any key to continue. startup container...'

mkdir /tmp
docker run -dit --restart unless-stopped \
  -u 501:20 -p 8000:18000 -p 443:10443 \
  -v .:/config \
  -v /tmp:/data \
  --name dnsrobocert-plus-nginx cr.h.rexzhang.com/ray1ex/dnsrobocert-plus-nginx
docker image prune -f
docker container logs -f dnsrobocert-plus-nginx
