#!/bin/sh

# 这似乎是一个系统级别的 bug,设置一下即可解决 worker CPU 占用 100% 的问题
#ulimit -n 65536;

# prepare data path
mkdir -p /data/lexicon_tld_set
mkdir -p /data/dnsrobocert
mkdir -p /data/nginx/http_server.d
mkdir -p /data/nginx/http_upstream.d
mkdir -p /data/nginx/stream_server.d
mkdir -p /logs/dnsrobocert
mkdir -p /logs/nginx
mkdir -p /logs/plush

# call plush init
run_plush_generate="python -m plush init"
while ! $run_plush_generate; do
    echo "Run plush init failed, retrying..."
    sleep 1
done

# start nginx service
start_nginx_service="/app/nginx/reload.sh"
while ! $start_nginx_service; do
    echo "Start NGINX failed, retrying..."
    sleep 1
done

# start dnsrobocert service
if [ "$DNSROBOCERT" = "enable" ]; then
    /usr/local/bin/dnsrobocert --config /config/dnsrobocert.yml --directory /data/dnsrobocert
else
    echo "ENV: DNSROBOCERT is not enable"
    python
fi

# for dev
if [ "$ENV" = "rex" ]; then python; fi
