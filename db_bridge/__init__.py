from importlib.metadata import version

__version__ = version("db-bridge")   # reads pyproject.toml metadata

from .config import load_config
from .db_utils import (
    run_sql,
    get_column_values,
    get_column_values_regexp,
)

__all__ = [
    "__version__",
    "load_config",
    "run_sql",
    "get_column_values",
    "get_column_values_regexp",
]
