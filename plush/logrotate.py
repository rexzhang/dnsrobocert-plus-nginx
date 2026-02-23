from logging import getLogger

from .deploy_stage import EV, get_file_path
from .tempalte import Template

logger = getLogger(__name__)
logrotate_conf_template = """
/logs/nginx/*.log {
        daily
        size {{ EV.LOGROTATE_SIZE }}
        rotate {{ EV.LOGROTATE_ROTATE }}
        dateext
        dateformat -%Y%m%d

        compress
        delaycompress

        missingok
        notifempty
        create 0664

        sharedscripts
        postrotate
                [ ! -f /run/nginx/nginx.pid ] || kill -USR1 $(cat /run/nginx/nginx.pid)
        endscript
}

/logs/supercronic.log {
        weekly
        rotate {{ EV.LOGROTATE_ROTATE }}

        compress
        delaycompress

        missingok
        notifempty
        create 0664

        copytruncate
}
"""


def generate_logrotate_conf():
    filename = get_file_path(EV.LOGROTATE_CONF)
    conf_content = Template().render(logrotate_conf_template, EV=EV)

    with open(filename, "w") as f:
        f.write(conf_content)

    message = f"logrotate file: {filename} generate finished."
    logger.info(message)
