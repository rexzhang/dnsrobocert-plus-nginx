#!/bin/sh

## run on non-root user
usermod -o -u "$UID" runner
groupmod -o -g "$GID" runner

echo "
------------------------
Runner uid: $(id -u runner)
Runner gid: $(id -g runner)
------------------------
"

chown -R runner:runner /data
chown -R runner:runner /nginx

su runner -c "/usr/local/bin/dnsrobocert --config /etc/dnsrobocert.yml --directory /data"
