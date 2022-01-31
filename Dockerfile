FROM python:3.9-alpine

ARG ENV

ENV UID=1000
ENV GID=1000

RUN if [ "$ENV" = "rex" ]; then echo "Change depends" \
    && pip config set global.index-url http://192.168.200.21:3141/root/pypi/+simple \
    && pip config set install.trusted-host 192.168.200.21 \
    && sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories \
    ; fi

COPY . /app

RUN \
    # install depends
    apk add --no-cache --virtual .build-deps build-base musl-dev python3-dev libffi-dev openssl-dev cargo ; \
    if [ "$ENV" = "rex" ]; then echo "Change depends" \
    && mkdir /root/.cargo && cp /app/cargo.config.toml /root/.cargo/config.toml \
    ; fi \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apk del .build-deps \
    && rm -rf /root/.cargo \
    && find /usr/local/lib/python*/ -type f -name '*.py[cod]' -delete \
    # create non-root user
    && apk add --no-cache shadow \
    && addgroup -S -g $GID runner \
    && adduser -S -D -G runner -u $UID runner \
    # prepare data path
    && mkdir /config \
    && mkdir /data

WORKDIR /app
VOLUME /data

CMD /app/entrypoint.sh
