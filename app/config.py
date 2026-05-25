from __future__ import annotations

from os import PathLike
from typing import Union

from dotenv import load_dotenv


EnvPath = Union[str, PathLike[str]]


def load_local_env(path: EnvPath | None = None) -> bool:
    return load_dotenv(dotenv_path=path, encoding="utf-8-sig")
