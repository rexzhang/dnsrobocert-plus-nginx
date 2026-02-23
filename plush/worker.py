import sched
import subprocess
import time
from logging import Formatter, getLogger
from logging.handlers import WatchedFileHandler

from .constants import NGINX_RELOAD_SH, WORKER_LOG, WORKER_PID
from .daemon_runner import DaemonRunner
from .deploy_stage import EV, DeployStage, get_file_path

logger = getLogger(__name__)
logger_formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _logging_add_file_handler():
    logger_handler = WatchedFileHandler(get_file_path(WORKER_LOG))
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)


def task_nginx_reload():
    logger.info("Worker: Reload NGINX ...")
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
    if EV.DEPLOY_STAGE == DeployStage.PRD:
        interval_seconds = 60 * 60 * 24 * 7  # 1 week
    else:
        interval_seconds = 10

    def task_func():
        # call real task function
        task_nginx_reload()
        # reschedule
        scheduler.enter(interval_seconds, 1, task_func, (scheduler,))

    # create scheduler
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(interval_seconds, 1, task_func, (scheduler,))

    # start schedule, blocking
    logger.info("Plush worker schedule starting...")
    scheduler.run()


class ScheduleDaemon(DaemonRunner):
    def __init__(self):
        super().__init__(
            pid_file=WORKER_PID, func_daemon=schedule_func, func_cleanup=None
        )
