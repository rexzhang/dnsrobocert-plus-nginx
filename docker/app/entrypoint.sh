#!/bin/sh

/usr/sbin/nginx -c /nginx/nginx.conf

/usr/local/bin/dnsrobocert --config /config/dnsrobocert.yml --directory /data/dnsrobocert

# for dev
if [ "$ENV" = "rex" ]; then python; fi
