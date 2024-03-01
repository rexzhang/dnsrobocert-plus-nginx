#!/bin/sh

# prepare data path
mkdir -p /data/lexicon_tld_set
mkdir -p /data/dnsrobocert
mkdir -p /data/nginx/http.d
mkdir -p /data/nginx/stream.d
mkdir -p /logs/dnsrobocert
mkdir -p /logs/nginx

# generate nginx *.conf file
run_plush_generate="python -m plush generate"
while ! $run_plush_generate; do
    echo "Run plush generate failed, retrying..."
    sleep 1
done

# start nginx service
start_nginx_service="/usr/sbin/nginx -e /logs/nginx/error.log"
while ! $start_nginx_service; do
    echo "Start NGINX failed, retrying..."
    sleep 1
done

# start dnsrobocert service
/usr/local/bin/dnsrobocert --config /config/dnsrobocert.yml --directory /data/dnsrobocert

# for dev
if [ "$ENV" = "rex" ]; then python; fi
