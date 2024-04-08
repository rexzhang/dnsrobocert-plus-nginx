from enum import Enum
from os import getenv
from pathlib import Path

"""The Twelve Factors
https://12factor.net/
"""


class Stage(Enum):
    DEV = "DEV"
    TEST = "TEST"
    ALPHA = "ALPHA"
    BETA = "BETA"
    PRODUCTION = "PRODUCTION"


_prefix = getenv("T12F_NAME", "T12F")
stage = Stage(getenv("T12F_STAGE", "PRODUCTION").upper())


def file(file: Path | str) -> Path | str:
    """还有一种思路:T12F_FILE_PREFIX"""
    if stage != Stage.DEV:
        return file

    return f"/tmp/{_prefix}" + Path(file).absolute().as_posix().replace("/", "_")
