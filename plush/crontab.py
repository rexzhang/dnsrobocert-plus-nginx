from logging import getLogger

from crontab import CronTab

from .deploy_stage import EV, get_path

logger = getLogger(__name__)

_CRON_COMMENT_TAG = "PLUSH"


def update_crontab_file():
    filename = get_path("/etc/crontabs/root").as_posix()

    cron = CronTab()
    cron.remove_all(comment=_CRON_COMMENT_TAG)
    job = cron.new(
        command="python -m plush cron",
        comment=_CRON_COMMENT_TAG,
    )
    job.setall(EV.CRONTAB)
    cron.write(get_path("/etc/crontabs/root").as_posix())

    message = f"Init: crontab file:{filename} created/updated."
    logger.info(message)
