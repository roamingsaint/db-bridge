# config.py

import os
import configparser
from dotenv import load_dotenv
from pathlib import Path

# Optional: load a .env file if python-dotenv is installed
try:
    load_dotenv()
except ImportError:
    pass


def load_config(profile_env_var: str = "DBBRIDGE_PROFILE") -> dict:
    """
    1) If DB_NAME, DB_USER & DB_PASS are in ENV → use those.
    2) Otherwise fallback to ~/.dbbridge.cfg:
       - pick section from [DEFAULT] → active (or first section)
    Returns a dict: host, port, database, user, password
    """
    # 1) ENV-first
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASS")
    if name and user and pwd:
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "database": name,
            "user": user,
            "password": pwd,
        }

    # 2) INI fallback
    cfg_path = Path.home() / ".dbbridge.cfg"
    if not cfg_path.exists():
        raise RuntimeError(
            "No DB config found: set DB_NAME/DB_USER/DB_PASS in ENV, "
            "or create ~/.dbbridge.cfg"
        )

    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)

    # choose which section to use
    active = os.getenv(profile_env_var) or cfg["DEFAULT"].get("active", None)
    if not active:
        sections = [s for s in cfg.sections()]
        if not sections:
            raise RuntimeError(f"No profiles defined in {cfg_path}")
        active = sections[0]

    if active not in cfg:
        raise RuntimeError(f"Profile '{active}' not found in {cfg_path}")

    sect = cfg[active]
    return {
        "host": sect.get("host", "localhost"),
        "port": int(sect.get("port", '3306')),
        "database": sect["name"],
        "user": sect["user"],
        "password": sect["password"],
    }
