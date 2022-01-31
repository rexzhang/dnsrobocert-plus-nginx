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

su runner -s /app/runserver.sh
