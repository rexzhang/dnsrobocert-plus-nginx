FROM python:3.14-alpine

ARG BUILD_ENV

ENV PYTHONPATH="/app"
ENV TLDEXTRACT_CACHE_PATH=/data/lexicon_tld_set

ENV PLUSH_DEPLOY_STAGE="prd"
ENV PLUSH_CRONTAB_FILE="/tmp/crontabs"
ENV DNSROBOCERT="enable"

RUN if [ "$BUILD_ENV" = "rex" ]; then echo "Change depends" && \
    pip config set global.index-url https://proxpi.h.rexzhang.com/index/ && \
    pip config set install.trusted-host proxpi.h.rexzhang.com && \
    sed -i 's#https\?://dl-cdn.alpinelinux.org/alpine#https://mirrors.tuna.tsinghua.edu.cn/alpine#g' /etc/apk/repositories \
    ; fi

COPY requirements.d /app/requirements.d
RUN \
    # install depends ---
    apk add --no-cache --virtual .build-deps build-base libffi-dev && \
    # -- for nginx
    apk add nginx nginx-mod-stream nginx-mod-mail nginx-mod-http-brotli nginx-mod-http-zstd && \
    chmod 777 -R /var/lib/nginx && \
    mkdir -p /run/nginx && \
    chmod 777 -R /run/nginx && \
    # -- for crontab
    apk add supercronic && \
    # -- for logrotate
    apk add logrotate && \
    # -- for py
    pip install --no-cache-dir -r /app/requirements.d/docker.txt && \
    # cleanup ---
    apk del .build-deps && \
    rm -rf /root/.cache && \
    find /usr/local/lib/python*/ -type f -name '*.py[cod]' -delete && \
    find /usr/local/lib/python*/ -type d -name "__pycache__" -delete && \
    # prepare config/data path ---
    mkdir /config && \
    mkdir /data && \
    mkdir /logs

COPY docker /app
COPY plush /app/plush
RUN \
    # nginx
    cp -f /app/nginx/nginx.conf /etc/nginx

VOLUME /config
VOLUME /data
VOLUME /logs

WORKDIR /app
CMD /app/entrypoint.sh
