#!/bin/sh

nginx_pid=$(pgrep /usr/sbin/nginx)

if [ -n "$nginx_pid" ]; then
    echo "NGINX is running, PID is $nginx_pid, Reloading..."
    /usr/sbin/nginx -e /logs/nginx/error.log -s reload
    echo "Restart NGINX done."
else
    echo "NGINX is not running, Starting..."
    /usr/sbin/nginx -e /logs/nginx/error.log
    echo "Start NGINX done."
fi
