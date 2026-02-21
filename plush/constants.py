from enum import StrEnum, auto

# NGINX
CONFIG_NGINX_TOML = "/config/nginx.toml"

NGINX_CONF_DIR = "/data/nginx"
NGINX_RELOAD_SH = "/app/nginx/reload.sh"  # 已废弃

NGINX_HTTP_DEFAULT_CONF = "http_default.conf"
NGINX_HTTP_DEFAULT_LISTEN = 10080
NGINX_HTTP_DEFAULT_LISTEN_SSL = 10443

NGINX_HTTP_UPSTREAM_DIR = "http_upstream.d"
NGINX_HTTP_SERVER_DIR = "http_server.d"

NGINX_STREAM_UPSTREAM_DIR = "stream_upstream.d"
NGINX_STREAM_SERVER_DIR = "stream_server.d"

NGINX_MAIL_SERVER_DIR = "mail_server.d"


class NginxMailServerType(StrEnum):
    SSL = auto()
    STARTTLS = auto()


# Worker
WORKER_PID = "/tmp/plush-worker.pid"
WORKER_LOG = "/logs/plush/worker.log"


# dnsrobocert
DNSROBOCERT_SSL_FILE_DIR = "/data/dnsrobocert/live"
