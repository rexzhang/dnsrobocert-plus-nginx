import subprocess
import time
from logging import Formatter, getLogger
from logging.handlers import WatchedFileHandler

import schedule

from plush import t12f
from plush.constants import NGINX_RELOAD_SH, WORKER_LOG, WORKER_PID
from plush.daemon_runner import DaemonRunner

logger = getLogger(__name__)
logger_formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _logging_add_file_handler():
    logger_handler = WatchedFileHandler(t12f.file(WORKER_LOG))
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)


def task_nginx_reload():
    try:
        result = subprocess.run(
            [
                NGINX_RELOAD_SH,
            ],
            capture_output=True,
        )

    except Exception as e:
        logger.error(e)
        return

    logger.info(f"Worker: Reload NGINX finished, returncode:{result.returncode}")
    logger.info(f"stdout: {result.stdout.decode('utf-8')}")
    if result.stderr:
        logger.info(f"stderr: {result.stderr.decode('utf-8')}")


def schedule_func(**kwargs):
    _logging_add_file_handler()  # fork, reopen file handle
    logger.info(f"Plush worker starting...pid: {kwargs.get('pid')}")

    # init schedule
    if t12f.stage == t12f.Stage.PRODUCTION:
        schedule.every().weeks.do(task_nginx_reload)
    else:
        schedule.every(10).seconds.do(task_nginx_reload)

    # run schedule task
    logger.info("Plush worker schedule starting...")
    while True:
        schedule.run_pending()
        time.sleep(1)


schedule_daemon = DaemonRunner(WORKER_PID, schedule_func)
