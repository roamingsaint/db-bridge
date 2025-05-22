from importlib.metadata import version

__version__ = version("dbbridge")   # reads pyproject.toml metadata

from .config import load_config
from .db_utils import run_sql

__all__ = ["__version__", "load_config", "run_sql"]
