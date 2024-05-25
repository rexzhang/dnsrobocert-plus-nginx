"""
- https://gist.github.com/rexzhang/fb3f1b9e13a5a78f2dd1e390062690d4
- https://peps.python.org/pep-3143
- https://pagure.io/python-daemon/blob/main/f/doc/examples/service-runner.txt
"""

import signal
import sys
from collections.abc import Callable
from logging import getLogger
from os import kill
from pathlib import Path

from daemon import DaemonContext
from daemon.pidfile import TimeoutPIDLockFile
from lockfile import AlreadyLocked

from plush import t12f

logger = getLogger(__name__)


class DaemonRunner:
    def __init__(
        self,
        pid_file: Path | str,
        func_daemon: Callable,
        func_cleanup: Callable | None = None,
    ) -> None:
        self.pid_file = t12f.file(pid_file)
        self.pid_lock = TimeoutPIDLockFile(self.pid_file)
        self.func_daemon = func_daemon
        self.func_cleanup = func_cleanup

    def _cleanup(self, signum, frame):
        logger.debug(f"DaemonRunner._cleanup({signum}, {frame})")

        if self.func_cleanup:
            self.func_cleanup()

        logger.info(f"Daemon(pid:{self.pid_lock.read_pid()}) cleanup finished")
        exit(0)

    def start(self, **kwargs):
        try:
            with DaemonContext(
                detach_process=True,
                pidfile=self.pid_lock,
                stdout=sys.stdout,
                stderr=sys.stderr,
                signal_map={
                    signal.SIGTERM: self._cleanup,
                    # signal.SIGHUP: "terminate",
                    # signal.SIGUSR1: reload_program_config,
                },
            ):
                pid = self.pid_lock.read_pid()
                kwargs.update({"pid": pid})

                logger.info(f"Daemon(pid:{pid}) starting...")
                self.func_daemon(**kwargs)

        except AlreadyLocked as e:
            logger.error(f"Daemon cannot start: {e}")
            return

        return

    def stop(self):
        pid = self.pid_lock.read_pid()
        if pid is None:
            logger.warning("Cannot get daemon pid")
            return

        logger.info(f"Daemon(pid:{pid}) stopping...")
        kill(pid, signal.SIGTERM)
