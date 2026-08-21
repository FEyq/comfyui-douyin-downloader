"""Local Cookie helpers used by the standalone Music Note Cookie tool."""

from __future__ import annotations

import configparser
import os
import tempfile
from pathlib import Path


CONFIG_FILE = Path(__file__).resolve().with_name("config.ini")


def normalize_cookie(value: str) -> str:
    """Convert a pasted Cookie header into a compact name=value list."""
    text = str(value or "").strip()
    if text.lower().startswith("cookie:"):
        text = text.split(":", 1)[1].strip()

    pairs = {}
    for item in text.replace("\r", ";").replace("\n", ";").split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        name, cookie_value = item.split("=", 1)
        name = name.strip()
        cookie_value = cookie_value.strip()
        if name and cookie_value:
            pairs[name] = cookie_value

    return "; ".join(f"{name}={cookie_value}" for name, cookie_value in pairs.items())


def validate_cookie(value: str) -> tuple[bool, str]:
    """Check that a Cookie contains a target-platform login session field."""
    normalized = normalize_cookie(value)
    items = {}
    for item in normalized.split("; "):
        if "=" in item:
            name, cookie_value = item.split("=", 1)
            items[name] = cookie_value

    if not items:
        return False, "没有识别到 Cookie 字段"
    if not any(key in items for key in ("sessionid", "sessionid_ss")):
        return False, "缺少 sessionid 或 sessionid_ss"
    if len(normalized) < 30:
        return False, "Cookie 内容过短，可能复制不完整"
    return True, f"已识别 {len(items)} 个字段"


def load_config() -> dict[str, str]:
    """Load optional local browser-path settings from config.ini."""
    config = {"chrome_path": "", "edge_path": "", "cookie": ""}
    if not CONFIG_FILE.is_file():
        return config

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(CONFIG_FILE, encoding="utf-8")
        if parser.has_section("main"):
            for key in config:
                config[key] = parser.get("main", key, fallback=config[key])
    except (OSError, configparser.Error):
        pass
    return config


def save_config(config: dict[str, str]) -> None:
    """Save local settings atomically; config.ini is ignored by Git."""
    parser = configparser.ConfigParser(interpolation=None)
    parser["main"] = {
        "chrome_path": config.get("chrome_path", ""),
        "edge_path": config.get("edge_path", ""),
        "cookie": config.get("cookie", ""),
    }
    fd, temp_name = tempfile.mkstemp(
        dir=str(CONFIG_FILE.parent), prefix=".config_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            parser.write(handle)
        os.replace(temp_name, CONFIG_FILE)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
