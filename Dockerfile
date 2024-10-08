FROM python:3.13-alpine

ARG ENV
ENV DEPLOY_HOOK="/app/nginx/reload.sh"
ENV TLDEXTRACT_CACHE_PATH=/data/lexicon_tld_set
ENV DNSROBOCERT="enable"

RUN if [ "$ENV" = "rex" ]; then echo "Change depends" \
    && pip config set global.index-url https://proxpi.h.rexzhang.com/index/ \
    && pip config set install.trusted-host proxpi.h.rexzhang.com \
    && sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories \
    ; fi

COPY docker /app
COPY plush /app/plush
COPY requirements /app/requirements

RUN \
    # install depends ---
    apk add --no-cache --virtual .build-deps build-base libffi-dev \
    # -- for nginx
    && apk add nginx nginx-mod-stream nginx-mod-http-brotli nginx-mod-http-zstd \
    && mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig \
    && mv /app/nginx/nginx.conf /etc/nginx \
    && chmod 777 -R /var/lib/nginx \
    ## && chmod 777 -R /var/log/nginx \
    && mkdir -p /run/nginx \
    && chmod 777 -R /run/nginx \
    # -- for py
    && pip install --no-cache-dir -r /app/requirements/docker.txt \
    # cleanup ---
    && apk del .build-deps \
    && rm -rf /root/.cache \
    && find /usr/local/lib/python*/ -type f -name '*.py[cod]' -delete \
    && find /usr/local/lib/python*/ -type d -name "__pycache__" -delete \
    # prepare config/data path ---
    && mkdir /config \
    && mkdir /data \
    && mkdir /logs

WORKDIR /app

VOLUME /config
VOLUME /data
VOLUME /logs

CMD /app/entrypoint.sh
