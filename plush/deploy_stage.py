from enum import StrEnum, auto
from logging import getLogger
from pathlib import Path

from dataclass_wizard import EnvWizard

logger = getLogger(__name__)


class DeployStage(StrEnum):
    UNKNOW = auto()

    LOCAL = auto()
    DEV = auto()
    TEST = auto()
    UAT = auto()

    PRD = auto()


class EnvValue(EnvWizard):
    class _(EnvWizard.Meta):
        env_prefix = "PLUSH_"
        env_file = True

    DEPLOY_STAGE: str = DeployStage.DEV

    CRONTAB_FILE: str = "/tmp/crontabs"
    CRONTAB_UPDATE: str = "0 0 2 * *"
    CRONTAB_LOGROTATE: str = "0 0 * * *"


EV = EnvValue()


def get_path(path: str | Path) -> Path:
    if isinstance(path, str):
        path = Path(path)

    if EV.DEPLOY_STAGE == DeployStage.DEV:

        return Path(f"/tmp/{Path(path).absolute().as_posix().replace("/", "_")}")
    else:
        return path
