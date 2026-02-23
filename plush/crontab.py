from logging import getLogger

from crontab import CronTab

from .deploy_stage import EV, get_file_path

logger = getLogger(__name__)

_CRON_COMMENT_TAG = "PLUSH"


def update_crontab_file():
    filename = get_file_path(EV.CRONTAB_FILE).as_posix()

    cron = CronTab()
    cron.remove_all(comment=_CRON_COMMENT_TAG)

    job = cron.new(command="/app/cron/update.sh", comment=_CRON_COMMENT_TAG)
    job.setall(EV.CRONTAB_UPDATE)

    job = cron.new(command="/app/cron/logrotate.sh", comment=_CRON_COMMENT_TAG)
    job.setall(EV.CRONTAB_LOGROTATE)
    cron.write(filename)

    message = f"Generate/update crontab file: {filename} finished."
    logger.info(message)
