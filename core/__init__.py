"""Final Fantasy Tactics Advance (GBA) Save File Editor - Core Engine.

Provides modular components for low-level save parsing, clan roster diagnostics,
character ability and item patching, recruit injection, and configuration.
"""

from .builder import (
    equip_unit_build,
    inject_unit,
    rename_unit,
    resolve_job_and_race,
)
from .config import (
    get_default_backup_dir,
    load_builds,
    load_config,
    parse_simple_toml,
)
from .patcher import (
    clear_clan_cards,
    patch_clan_units,
    patch_super_starter,
)
from .roster import (
    display_roster,
    get_item_name,
    inspect_save,
)
from .save import (
    MAGIC,
    SECTOR_SIZE,
    atomic_write,
    auto_detect_save,
    compute_crc,
    create_snapshot_backup,
    fix_crc,
    get_slots,
)

__all__ = [
    "MAGIC",
    "SECTOR_SIZE",
    "atomic_write",
    "auto_detect_save",
    "clear_clan_cards",
    "compute_crc",
    "create_snapshot_backup",
    "display_roster",
    "equip_unit_build",
    "fix_crc",
    "get_default_backup_dir",
    "get_item_name",
    "get_slots",
    "inject_unit",
    "inspect_save",
    "load_builds",
    "load_config",
    "parse_simple_toml",
    "patch_clan_units",
    "patch_super_starter",
    "rename_unit",
    "resolve_job_and_race",
]
