"""Configuration and builds database loading for ffta_tool."""

import os
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def parse_simple_toml(content: str) -> dict:
    """Minimal fallback TOML parser for basic key/value tables and lists."""
    data = {}
    current_section = data
    in_list_key = None
    list_accumulator = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if in_list_key is not None:
            clean_part = line.split("#")[0].strip()
            if "]" in clean_part:
                before_bracket = clean_part.split("]")[0].strip()
                if before_bracket:
                    list_accumulator.append(before_bracket)
                full_str = "".join(list_accumulator)
                items = []
                for item in full_str.split(","):
                    item = item.strip()
                    if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
                        items.append(item[1:-1])
                    elif item.isdigit():
                        items.append(int(item))
                    elif item:
                        items.append(item)
                current_section[in_list_key] = items
                in_list_key = None
                list_accumulator = []
            else:
                list_accumulator.append(clean_part)
            continue

        if line.startswith("[") and line.endswith("]"):
            sec_name = line[1:-1].strip()
            current_section = data.setdefault(sec_name, {})
            continue

        if "=" in line:
            clean_line = line.split("#")[0].strip()
            key, val = clean_line.split("=", 1)
            key = key.strip()
            val = val.strip()

            if val.startswith("[") and not val.endswith("]"):
                in_list_key = key
                list_accumulator = [val[1:].strip()]
                continue

            if val.lower() == "true":
                current_section[key] = True
            elif val.lower() == "false":
                current_section[key] = False
            elif val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
                current_section[key] = int(val)
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                current_section[key] = val[1:-1]
            elif val.startswith("[") and val.endswith("]"):
                items = []
                inside = val[1:-1].strip()
                if inside:
                    for item in inside.split(","):
                        is_quoted = (item.startswith('"') and item.endswith('"')) or (
                            item.startswith("'") and item.endswith("'")
                        )
                        if is_quoted:
                            items.append(item[1:-1])
                        elif item.isdigit():
                            items.append(int(item))
                        elif item:
                            items.append(item)
                current_section[key] = items
            else:
                current_section[key] = val

    return data


def load_config(config_path=None) -> dict:
    """Loads configuration from a TOML file.

    Search priority:
    1. Explicit config_path (from --config)
    2. ./config.toml (working directory)
    3. $XDG_CONFIG_HOME/ffta-tool/config.toml or ~/.config/ffta-tool/config.toml
    """
    target = None
    if config_path:
        target = Path(os.path.expanduser(config_path))
        if not target.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        local_cfg = Path("config.toml")
        if local_cfg.is_file():
            target = local_cfg
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                user_cfg = Path(xdg_config) / "ffta-tool" / "config.toml"
            else:
                user_cfg = Path.home() / ".config" / "ffta-tool" / "config.toml"
            if user_cfg.is_file():
                target = user_cfg

    if not target:
        return {}

    with open(target, encoding="utf-8") as f:
        content = f.read()

    if tomllib is not None:
        try:
            return tomllib.loads(content)
        except Exception:
            return parse_simple_toml(content)
    return parse_simple_toml(content)


def get_default_backup_dir(custom_dir=None) -> Path:
    """Returns the backup directory path, expanding tilde if needed."""
    if custom_dir:
        return Path(os.path.expanduser(str(custom_dir)))
    home = os.environ.get("HOME")
    if home:
        return Path(home) / "Documents" / "FFTA_Backups"
    return Path.cwd() / "backups"


def load_builds(builds_path=None) -> dict:
    """Loads builds database from TOML file."""
    target = None
    if builds_path:
        target = Path(os.path.expanduser(builds_path))
    else:
        local_b = Path("builds.toml")
        if local_b.is_file():
            target = local_b
        else:
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                user_b = Path(xdg_config) / "ffta-tool" / "builds.toml"
            else:
                user_b = Path.home() / ".config" / "ffta-tool" / "builds.toml"
            if user_b.is_file():
                target = user_b

    if not target or not target.is_file():
        return {}

    with open(target, encoding="utf-8") as f:
        content = f.read()

    if tomllib is not None:
        try:
            return tomllib.loads(content).get("builds", {})
        except Exception:
            return parse_simple_toml(content).get("builds", {})
    return parse_simple_toml(content).get("builds", {})
