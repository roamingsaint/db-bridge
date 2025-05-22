import configparser
import os
from pathlib import Path

from dotenv import load_dotenv

# Optional: load a .env file if python-dotenv is installed
try:
    load_dotenv()
except ImportError:
    pass


def load_config(profile_env_var: str = "DB_BRIDGE_PROFILE") -> dict:
    """
    1) ENV-first: if DB_NAME/DB_USER/DB_PASS are set in .env, use those.
    2) INI fallback: look for ~/.db_bridge.cfg, where ~ comes from HOME or USERPROFILE.
       Section = [DEFAULT].active or first section.
    Returns a dict: host, port, database, user, password
    """
    # 1) ENV-first
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASS")
    if name and user and pwd:
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 3306)),
            "database": name,
            "user": user,
            "password": pwd,
        }

    # 2) INI fallback
    home_dir = Path(os.getenv("HOME") or os.getenv("USERPROFILE") or Path.home())
    cfg_path = home_dir / ".db_bridge.cfg"
    if not cfg_path.exists():
        raise RuntimeError(
            "No DB config found: set DB_NAME/DB_USER/DB_PASS in ENV, "
            "or create ~/.db_bridge.cfg"
        )

    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)

    active = os.getenv(profile_env_var) or cfg["DEFAULT"].get("active", None)
    if not active:
        sections = cfg.sections()
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
