FROM python:3.11-alpine

ARG ENV
ENV TZ="Asia/Shanghai"

RUN if [ "$ENV" = "rex" ]; then echo "Change depends" \
    && pip config set global.index-url http://192.168.200.26:13141/root/pypi/+simple \
    && pip config set install.trusted-host 192.168.200.26 \
    && sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories \
    ; fi

COPY docker /
COPY plush /app/plush
COPY requirements /app

RUN \
    # install depends ---
    apk add --no-cache --virtual .build-deps build-base libffi-dev \
    # -- for nginx
    && apk add nginx nginx-mod-stream \
    && chmod 777 -R /var/lib/nginx \
    && chmod 777 -R /var/log/nginx \
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
    && mkdir /data

WORKDIR /app

VOLUME /config
VOLUME /data

CMD /app/entrypoint.sh
