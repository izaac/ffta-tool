#!/usr/bin/env python3
"""Final Fantasy Tactics Advance (GBA) - Ultimate Save Tool & Clan Manager.

A hardened, battle-tested utility for inspecting, managing, and patching
Final Fantasy Tactics Advance (GBA) Flash 64K / 128K wear-leveled save files.
"""

from core.builder import (
    equip_unit_build,
    inject_unit,
    rename_unit,
    resolve_job_and_race,
)
from core.cli import main
from core.config import (
    get_default_backup_dir,
    load_builds,
    load_config,
    parse_simple_toml,
)
from core.patcher import (
    MONSTER_SPECIES,
    clear_clan_cards,
    inject_monster_bank,
    pack_monster_stats,
    patch_clan_units,
    patch_super_starter,
    unpack_monster_stats,
)
from core.roster import (
    display_roster,
    get_item_name,
    inspect_save,
)
from core.save import (
    MAGIC,
    SECTOR_SIZE,
    atomic_write,
    auto_detect_save,
    compute_crc,
    create_snapshot_backup,
    fix_crc,
    get_slots,
)
from mappings import (
    CONSUMABLE_IDS,
    DEFAULT_COMBO_IDS,
    DEFAULT_REACTION_IDS,
    DEFAULT_SECONDARY_A_SETS,
    DEFAULT_SECONDARY_JOBS,
    DEFAULT_SUPPORT_IDS,
    EQUIPMENT_IDS,
    JOB_NAMES,
    JOB_PRIMARY_A_SETS,
    KNOWN_ITEMS,
    RACE_ABILITY_BASE,
    RACE_ABILITY_SPECS,
    RACE_JOB_COUNTERS,
    RACE_NAMES,
    RECRUIT_NAMES,
    compute_god_stats,
    generate_random_name,
    get_name_id_by_str,
    get_unit_name,
)

__all__ = [
    "CONSUMABLE_IDS",
    "DEFAULT_COMBO_IDS",
    "DEFAULT_REACTION_IDS",
    "DEFAULT_SECONDARY_A_SETS",
    "DEFAULT_SECONDARY_JOBS",
    "DEFAULT_SUPPORT_IDS",
    "EQUIPMENT_IDS",
    "JOB_NAMES",
    "JOB_PRIMARY_A_SETS",
    "KNOWN_ITEMS",
    "MAGIC",
    "RACE_ABILITY_BASE",
    "RACE_ABILITY_SPECS",
    "RACE_JOB_COUNTERS",
    "RACE_NAMES",
    "RECRUIT_NAMES",
    "SECTOR_SIZE",
    "atomic_write",
    "auto_detect_save",
    "clear_clan_cards",
    "compute_crc",
    "compute_god_stats",
    "create_snapshot_backup",
    "display_roster",
    "equip_unit_build",
    "fix_crc",
    "generate_random_name",
    "get_default_backup_dir",
    "get_item_name",
    "get_name_id_by_str",
    "get_slots",
    "get_unit_name",
    "inject_monster_bank",
    "inject_unit",
    "inspect_save",
    "load_builds",
    "load_config",
    "main",
    "MONSTER_SPECIES",
    "pack_monster_stats",
    "parse_simple_toml",
    "patch_clan_units",
    "patch_super_starter",
    "rename_unit",
    "resolve_job_and_race",
    "unpack_monster_stats",
]

if __name__ == "__main__":
    main()
