# db_bridge/config.py

import configparser
import os
from pathlib import Path
from typing import Dict, Any


def load_config(profile_name: str = None) -> Dict[str, Any]:
    """
    Load DB credentials from ~/.db_bridge.cfg, or (if set and exists) from $DB_BRIDGE_CONFIG.

    Args:
        profile_name: Name of the section to load. If None, uses [DEFAULT].active or the first section.

    Environment:
        DB_BRIDGE_CONFIG: path to an alternate .cfg file (used only if that file exists).
    """

    # 1) Determine config file path
    cfg_env = os.getenv("DB_BRIDGE_CONFIG", "").strip()
    if cfg_env and Path(cfg_env).is_file():
        cfg_path = Path(cfg_env)
    else:
        home = os.getenv("HOME") or os.getenv("USERPROFILE") or None
        base = Path(home) if home else Path.home()
        cfg_path = base / ".db_bridge.cfg"

    if not cfg_path.is_file():
        raise RuntimeError(
            f"No DB config found at {cfg_path}. "
            "Please create ~/.db_bridge.cfg or set DB_BRIDGE_CONFIG correctly."
        )

    # 2) Parse the file
    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)

    # 3) Pick the profile/section
    if profile_name:
        active = profile_name
    else:
        active = cfg["DEFAULT"].get("active", None)

    if not active:
        sections = cfg.sections()
        if not sections:
            raise RuntimeError(f"No profiles defined in {cfg_path}")
        active = sections[0]

    if active not in cfg:
        raise RuntimeError(f"Profile '{active}' not found in {cfg_path}")

    sect = cfg[active]

    # 4) Build creds dict
    driver = sect.get("driver", "mysql").lower()
    creds = {"driver": driver}

    if driver == "sqlite":
        raw_path = sect.get("database") or sect.get("path")
        if not raw_path:
            raise RuntimeError(
                f"SQLite profile '{active}' requires a 'database = /path/to/file.db'"
            )

        # Expand leading '~' to the user's home directory
        db_path = Path(raw_path).expanduser().as_posix()

        creds["database"] = db_path
    else:
        creds.update({
            "host": sect.get("host", fallback="localhost"),
            "port": sect.getint("port", fallback=(5432 if driver == "postgres" else 3306)),
            "database": sect.get("database") or sect.get("name"),
            "user": sect["user"],
            "password": sect["password"],
        })

    return creds
