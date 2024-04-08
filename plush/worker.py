import subprocess
import sys
import time
from logging import Formatter, getLogger
from logging.handlers import WatchedFileHandler

import daemon
import fasteners
import schedule

from plush import t12f
from plush.constants import (
    WORKER_PID,
    WORKER_LOG,
    NGINX_RELOAD_SH,
)

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


def daemon_main():
    _logging_add_file_handler()  # fork, reopen file handle
    logger.info("Plush worker starting...")

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


def worker_main():
    pidfile = fasteners.InterProcessLock(t12f.file(WORKER_PID))
    try:
        with daemon.DaemonContext(
            detach_process=True, pidfile=pidfile, stdout=sys.stdout, stderr=sys.stderr
        ):
            daemon_main()

    except PermissionError as e:
        logger.critical(f"Cannot lock pid; {e}")
        exit(1)
