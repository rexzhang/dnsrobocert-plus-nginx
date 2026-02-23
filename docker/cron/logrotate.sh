#!/bin/sh

# logrotate
/usr/sbin/logrotate -s /tmp/logrotate.status "$PLUSH_LOGROTATE_CONF"
