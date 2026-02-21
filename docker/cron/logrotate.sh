#!/bin/sh

# logrotate
/usr/sbin/logrotate -s /tmp/logrotate.status /app/logrotate.conf
