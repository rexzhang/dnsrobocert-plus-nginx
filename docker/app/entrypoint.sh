#!/bin/sh

# prepare data path
mkdir -p /data/dnsrobocert
mkdir -p /data/nginx/http.d
mkdir -p /data/nginx/stream.d

# generate nginx *.conf file
python -m plush generate

# start nginx service
/usr/sbin/nginx -c /nginx/nginx.conf

# start dnsrobocert service
/usr/local/bin/dnsrobocert --config /config/dnsrobocert.yml --directory /data/dnsrobocert

# for dev
if [ "$ENV" = "rex" ]; then python; fi
