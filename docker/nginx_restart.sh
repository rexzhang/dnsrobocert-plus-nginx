#!/bin/sh

nginx_pid=$(pgrep nginx)

if [ -n "$nginx_pid" ]; then
    echo "Nginx is running, PID is $nginx_pid"
    /usr/sbin/nginx -s reload
else
    echo "Nginx is not running"
    /usr/sbin/nginx
fi
