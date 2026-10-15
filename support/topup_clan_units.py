#!/usr/bin/env python3
"""FFTA Clan Unit Top-Up & Optimization Tool.

Tops up existing clan units with:
- Non-destructive 115% god roll stats: max(current, god_stat) to preserve
  organic high-speed rolls while elevating all sub-optimal stats to top tier.
- 100% mastered abilities and unlocked advanced jobs.
- Optimal endgame meta gear from builds.toml.
- Duplicate primary/secondary skill prevention.
- Card clearing and jail pardons.
"""

import argparse
import os
import struct
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.builder import equip_unit_build
from core.patcher import inject_monster_bank
from core.save import (
    SECTOR_SIZE,
    atomic_write,
    compute_crc,
    create_snapshot_backup,
    get_slots,
)
from mappings import (
    ALTERNATE_SECONDARY_A_SETS,
    ALTERNATE_SECONDARY_JOBS,
    DEFAULT_SECONDARY_A_SETS,
    DEFAULT_SECONDARY_JOBS,
    JOB_NAMES,
    RACE_ABILITY_SPECS,
    RACE_JOB_COUNTERS,
    RACE_NAMES,
    compute_god_stats,
    get_unit_name,
)
from support.sync_pocket import DEFAULT_ASSET_DIR, sync_pocket
from support.validate_saves import validate_save_file

DEFAULT_SAVE_PATH = os.environ.get(
    "FFTA_SAVE_PATH",
    os.path.join(DEFAULT_ASSET_DIR, "Final Fantasy Tactics Advance (U) [!].sav"),
)
BUILDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "builds.toml"))


def topup_unit(
    sav_data: bytearray,
    sec0_offset: int,
    unit_idx: int,
) -> dict:
    """Tops up a single clan unit with god-rolled stats and mastered abilities."""
    u_addr = sec0_offset + 0x80 + unit_idx * 0x108
    ub = sav_data[u_addr : u_addr + 0x108]

    level = ub[0x09]
    if level == 0:
        return {}

    name_id = struct.unpack("<H", ub[0:2])[0]
    flag = ub[0x04]
    name = get_unit_name(name_id, special_flag=flag)
    race_id = ub[0x06]
    job_id = ub[0x07]
    race_name = RACE_NAMES.get(race_id, "Unknown")
    job_name = JOB_NAMES.get(job_id, ("Unknown", ""))[0]

    # Current stats
    cur_hp, cur_max_hp, cur_mp, cur_max_mp, cur_watk, cur_wdef, cur_mpow, cur_mres = struct.unpack("<8H", ub[0x18:0x28])
    cur_spd = struct.unpack("<H", ub[0xD2:0xD4])[0]

    # Compute 115% top-rolled god stats
    god = compute_god_stats(job_id, level=level)

    # Non-destructive upgrade: take max(current, god)
    new_hp = max(cur_max_hp, god["hp"])
    new_mp = max(cur_max_mp, god["mp"])
    new_watk = max(cur_watk, god["watk"])
    new_wdef = max(cur_wdef, god["wdef"])
    new_mpow = max(cur_mpow, god["mpow"])
    new_mres = max(cur_mres, god["mres"])
    new_spd = max(cur_spd, god["speed"])

    ub[0x18:0x28] = struct.pack(
        "<8H",
        new_hp,
        new_hp,
        new_mp,
        new_mp,
        new_watk,
        new_wdef,
        new_mpow,
        new_mres,
    )
    ub[0xD2:0xD4] = struct.pack("<H", new_spd)

    # Master all abilities for race
    if race_id in RACE_ABILITY_SPECS:
        count, blue_magic, morpher = RACE_ABILITY_SPECS[race_id]
        for i in range(count):
            ub[0x41 + i] = 0xE4
        if blue_magic:
            for i in range(blue_magic):
                ub[0x9C + i] = 0xE4
        if morpher:
            for i in range(12):
                ub[0x93 + i] = 0xE4

    # Unlock advanced jobs
    if race_id in RACE_JOB_COUNTERS:
        ub[0xF1:0x106] = RACE_JOB_COUNTERS[race_id]

    # Verify primary and secondary A-sets do not duplicate
    p_set = ub[0x35]
    s_set = ub[0x36]
    p_job = ub[0x07]
    s_job = ub[0x08]
    if p_set == s_set or p_job == s_job:
        def_sec = DEFAULT_SECONDARY_JOBS.get(race_id, p_job)
        if def_sec == p_job:
            ub[0x08] = ALTERNATE_SECONDARY_JOBS.get(race_id, p_job)
            ub[0x36] = ALTERNATE_SECONDARY_A_SETS.get(race_id, 4)
        else:
            ub[0x08] = def_sec
            ub[0x36] = DEFAULT_SECONDARY_A_SETS.get(race_id, 4)

    # Clear cards and jail status
    ub[0x101] = 0x00
    ub[0x102] = 0x00
    ub[0x103] = 0x00
    ub[0x104] = 0xFF
    if (ub[0x28] & 0x08) != 0:
        ub[0x28] &= ~0x08

    sav_data[u_addr : u_addr + 0x108] = ub

    return {
        "unit": unit_idx,
        "name": name,
        "race": race_name,
        "job": job_name,
        "level": level,
        "old_stats": (cur_max_hp, cur_max_mp, cur_watk, cur_wdef, cur_mpow, cur_mres, cur_spd),
        "new_stats": (new_hp, new_mp, new_watk, new_wdef, new_mpow, new_mres, new_spd),
    }


def topup_save(
    save_path: str = DEFAULT_SAVE_PATH,
    target_slot: int = 1,  # Slot 2 (index 1)
    target_units: list[int] | None = None,
    sync: bool = False,
    monster_level: int = 30,
    monster_stats: int | None = None,
) -> bool:
    """Tops up clan units in the specified save slot."""
    if not os.path.exists(save_path):
        print(f"[-] Save file not found: {save_path}")
        return False

    # 1. Create safety backup
    backup_path = create_snapshot_backup(save_path, action_name="topup_clan")
    print(f"[+] Snapshot backup created: {backup_path}")

    with open(save_path, "rb") as f:
        sav_data = bytearray(f.read())

    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in save file!")

    info = slots[target_slot]
    sec0_off = info["sectors"][0] * SECTOR_SIZE

    units = target_units if target_units is not None else list(range(2, 11))

    print(f"\n{'=' * 78}")
    print(f"TOPPING UP {len(units)} CLAN UNITS IN SLOT {target_slot + 1}")
    print(f"Target Save: {save_path}")
    print(f"{'=' * 78}")

    for u in units:
        res = topup_unit(sav_data, sec0_off, u)
        if not res:
            continue
        oh, om, ow, od, op, or_, os_ = res["old_stats"]
        nh, nm, nw, nd, np, nr, ns = res["new_stats"]
        print(
            f"  [+] Unit {u:2d}: {res['name']:<10} ({res['race']} {res['job']}, Lv {res['level']})\n"
            f"      Old: HP {oh:3d}, MP {om:3d}, Atk {ow:3d}, Def {od:3d}, Pow {op:3d}, Res {or_:3d}, Spd {os_:3d}\n"
            f"      New: HP {nh:3d}, MP {nm:3d}, Atk {nw:3d}, Def {nd:3d}, Pow {np:3d}, Res {nr:3d}, Spd {ns:3d}"
        )

    # 2. Equip meta loadouts from builds.toml for target units
    print("\n[*] Equipping optimal meta loadouts from builds.toml...")
    for u in units:
        equip_unit_build(
            sav_data,
            target_slot=target_slot,
            target_unit=u,
            builds_path=BUILDS_PATH,
            bump_counter=False,
        )

    # 3. Populate Monster Bank with all 20 monsters
    print("\n[*] Populating Cyril Monster Bank with all 20 monsters...")
    inject_monster_bank(
        sav_data,
        target_slot=target_slot,
        level=monster_level,
        stats=monster_stats,
        bump_counter=False,
    )

    # 4. Increment wear-leveling sequence counter and recompute CRC
    hdr_sec = info["sectors"][0]
    hdr_off = hdr_sec * SECTOR_SIZE
    new_counter = info["counter"] + 1
    sav_data[hdr_off + 8 : hdr_off + 12] = struct.pack("<I", new_counter)

    crc = compute_crc(sav_data, info["sectors"])
    sav_data[hdr_off + 0x0C : hdr_off + 0x10] = struct.pack("<I", crc)
    print(f"\n[+] Sequence counter incremented to: {new_counter}")
    print(f"[+] Checksum updated: {hex(crc)}")

    # 4. Atomic write
    atomic_write(save_path, sav_data)
    print(f"[+] Save successfully written: {save_path}")

    # 5. Validate
    validate_save_file(save_path, verbose=False)

    # 6. Sync to Pocket if requested
    if sync:
        print("\n[*] Syncing updated save to Analogue Pocket...")
        sync_pocket()

    return True


def main():
    parser = argparse.ArgumentParser(description="FFTA Clan Unit Top-Up & Optimization Tool")
    parser.add_argument("save_path", nargs="?", default=DEFAULT_SAVE_PATH, help="Path to .sav file")
    parser.add_argument("--slot", type=int, default=2, choices=[1, 2], help="Target save slot (1 or 2)")
    parser.add_argument(
        "--units",
        default="2,3,4,5,6,7,8,9,10",
        help="Comma-separated unit indices to top up (default: 2,3,4,5,6,7,8,9,10)",
    )
    parser.add_argument(
        "--monster-level",
        type=int,
        default=30,
        help="Level for Cyril Monster Bank monsters (1..99, default: 30)",
    )
    parser.add_argument(
        "--monster-stats",
        type=int,
        default=None,
        help="Base stats for Cyril Monster Bank monsters (50..999, default: level * 10 or 300)",
    )
    parser.add_argument("--sync", action="store_true", help="Sync to Analogue Pocket SD card")
    args = parser.parse_args()

    # Safety guards
    if args.monster_level is not None and not (1 <= args.monster_level <= 99):
        parser.error(f"--monster-level must be between 1 and 99 (got {args.monster_level})")

    if args.monster_stats is not None and not (1 <= args.monster_stats <= 999):
        parser.error(f"--monster-stats must be between 1 and 999 (got {args.monster_stats})")

    try:
        unit_list = [int(x.strip()) for x in args.units.split(",") if x.strip()]
        for u in unit_list:
            if not (0 <= u <= 23):
                parser.error(f"Unit index must be between 0 and 23 (got {u})")
    except ValueError:
        parser.error(f"Invalid units list format: {args.units}")
    topup_save(
        save_path=args.save_path,
        target_slot=args.slot - 1,
        target_units=unit_list,
        sync=args.sync,
        monster_level=args.monster_level,
        monster_stats=args.monster_stats,
    )


if __name__ == "__main__":
    main()
