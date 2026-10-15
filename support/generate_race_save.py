#!/usr/bin/env python3
"""FFTA Race Save File and Fleet Generator.

Generates canonical race-specific saves and ROM copies for:
- Hume (all 11 Hume jobs)
- Bangaa (all 7 Bangaa jobs)
- Moogle (all 8 Moogle jobs)
- Viera (all 8 Viera jobs)
- Nu Mou (all 8 Nu Mou jobs)

Configures Marche (Lv 9 god-rolled Blue Mage / Fighter, 146 Spd), Montblanc
(Lv 8 Gunner / Mog Knight), injects 100% mastered, meta-equipped recruits for
each job in the target race, and clears leftover slots.
"""

import argparse
import os
import shutil
import struct
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.builder import inject_unit
from core.patcher import inject_monster_bank
from core.save import SECTOR_SIZE, atomic_write, compute_crc, get_slots
from mappings import (
    RACE_ABILITY_SPECS,
    RACE_JOB_COUNTERS,
    compute_god_stats,
)
from support.sync_pocket import DEFAULT_ASSET_DIR, sync_pocket
from support.validate_saves import validate_save_file

DEFAULT_BASE_SAV = os.path.join(DEFAULT_ASSET_DIR, "Final Fantasy Tactics Advance (U) [!].sav")
DEFAULT_BASE_ROM = os.path.join(DEFAULT_ASSET_DIR, "Final Fantasy Tactics Advance (U) [!].gba")
BUILDS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "builds.toml"))

RACE_JOB_MAP = {
    "hume": [
        "paladin",
        "fighter",
        "blue_mage",
        "thief",
        "ninja",
        "illusionist_hume",
        "black_mage_hume",
        "white_mage_hume",
        "soldier",
        "archer_hume",
        "hunter",
    ],
    "bangaa": [
        "warrior",
        "dragoon",
        "defender",
        "gladiator",
        "white_monk",
        "bishop",
        "templar",
    ],
    "moogle": [
        "mog_knight",
        "gunner",
        "juggler",
        "animist",
        "thief_moogle",
        "gadgeteer",
        "black_mage_moogle",
        "time_mage_moogle",
    ],
    "viera": [
        "fencer",
        "elementalist",
        "red_mage",
        "white_mage",
        "summoner",
        "archer",
        "assassin",
        "sniper",
    ],
    "nu_mou": [
        "sage",
        "morpher",
        "time_mage_numou",
        "alchemist",
        "illusionist_numou",
        "beastmaster",
        "black_mage_numou",
        "white_mage_numou",
    ],
}

RACE_TITLES = {
    "hume": "Hume",
    "bangaa": "Bangaa",
    "moogle": "Moogle",
    "viera": "Viera",
    "nu_mou": "Nu Mou",
}


def setup_marche(sav_data: bytearray, sec0_offset: int):
    """Sets Marche to Lv 9 Blue Mage / Fighter god stats with Dual Tulwars and Acacia Hat."""
    u_addr = sec0_offset + 0x80
    ub = sav_data[u_addr : u_addr + 0x108]

    # Name ID 33 = Marche, Flag 2 = Marche, Sprite 2 = Blue Mage
    ub[0x00:0x02] = struct.pack("<H", 33)
    ub[0x04] = 2
    ub[0x05] = 80  # Sprite index
    ub[0x06] = 1   # Race Hume
    ub[0x07] = 10  # Primary Blue Mage (0x0A)
    ub[0x08] = 4   # Secondary Fighter (0x04)
    ub[0x09] = 9   # Level 9

    # God stats
    god = compute_god_stats(10, level=9)
    ub[0x18:0x28] = struct.pack(
        "<8H",
        god["hp"], god["hp"],
        god["mp"], god["mp"],
        god["watk"], god["wdef"],
        god["mpow"], god["mres"],
    )

    # Equipment: Tulwar (0x26), Tulwar (0x26), Acacia Hat (0x11E), Ninja Gear (0x138), Fairy Shoes (0x15A)
    ub[0x2A:0x34] = struct.pack("<5H", 0x0026, 0x0026, 0x011E, 0x0138, 0x015A)

    ub[0x34] = 142  # Race ability base
    ub[0x35] = 11   # Primary A-Set: Blue Magic
    ub[0x36] = 4    # Secondary A-Set: Fighter Tech
    ub[0x3A] = 31   # Reflex
    ub[0x3B] = 56   # Double Sword
    ub[0x3C] = 117  # Blue Combo

    # Master all Hume abilities (140) + Blue Magic (26)
    count, bm, _ = RACE_ABILITY_SPECS[1]
    for i in range(count):
        ub[0x41 + i] = 0xE4
    for i in range(bm):
        ub[0x9C + i] = 0xE4

    # Speed 146
    ub[0xD2:0xD4] = struct.pack("<H", 146)
    ub[0xF1:0x106] = RACE_JOB_COUNTERS[1]
    ub[0x101] = 0x00
    ub[0x102] = 0x00
    ub[0x103] = 0x00
    ub[0x104] = 0xFF

    sav_data[u_addr : u_addr + 0x108] = ub


def setup_montblanc(sav_data: bytearray, sec0_offset: int):
    """Sets Montblanc to Lv 8 Gunner / Mog Knight god stats."""
    u_addr = sec0_offset + 0x80 + 0x108
    ub = sav_data[u_addr : u_addr + 0x108]

    # Montblanc Name ID 102, Flag 8, Sprite 82
    ub[0x00:0x02] = struct.pack("<H", 102)
    ub[0x04] = 8
    ub[0x05] = 82  # Sprite index
    ub[0x06] = 5   # Moogle
    ub[0x07] = 38  # Gunner (0x26)
    ub[0x08] = 37  # Mog Knight (0x25)
    ub[0x09] = 8   # Level 8

    god = compute_god_stats(38, level=8)
    ub[0x18:0x28] = struct.pack(
        "<8H",
        god["hp"], god["hp"],
        god["mp"], god["mp"],
        god["watk"], god["wdef"],
        god["mpow"], god["mres"],
    )

    # Equipment: Calling Gun (0xFC), Thief Hat (0x11B), Ninja Gear (0x138), Ninja Tabi (0x15C), Angel Ring (0x165)
    ub[0x2A:0x34] = struct.pack("<5H", 0x00FC, 0x011B, 0x0138, 0x015C, 0x0165)

    ub[0x34] = 88   # Moogle ability base
    ub[0x35] = 28   # Primary A-Set: Gunmanship
    ub[0x36] = 32   # Secondary A-Set: Charge
    ub[0x3A] = 64   # Damage > MP
    ub[0x3B] = 30   # Concentrate
    ub[0x3C] = 31   # Gun Combo

    # Master all Moogle abilities
    count, _, _ = RACE_ABILITY_SPECS[5]
    for i in range(count):
        ub[0x41 + i] = 0xE4

    ub[0xD2:0xD4] = struct.pack("<H", 141)
    ub[0xF1:0x106] = RACE_JOB_COUNTERS[5]
    ub[0x101] = 0x00
    ub[0x102] = 0x00
    ub[0x103] = 0x00
    ub[0x104] = 0xFF

    sav_data[u_addr : u_addr + 0x108] = ub


def clear_unit_slot(sav_data: bytearray, sec0_offset: int, unit_idx: int):
    """Blanks an empty unit slot in Sector 0."""
    u_addr = sec0_offset + 0x80 + unit_idx * 0x108
    sav_data[u_addr : u_addr + 0x108] = b"\x00" * 0x108


def generate_race_fleet(
    race_key: str,
    base_sav_path: str = DEFAULT_BASE_SAV,
    base_rom_path: str = DEFAULT_BASE_ROM,
    output_dir: str = DEFAULT_ASSET_DIR,
    target_slot: int = 1,  # Slot 2 (index 1)
    level: int = 8,
    sync: bool = False,
) -> tuple[str, str]:
    """Generates a complete race fleet save and ROM."""
    norm_race = race_key.lower().replace(" ", "_").replace("-", "_")
    if norm_race not in RACE_JOB_MAP:
        raise ValueError(f"Unknown race '{race_key}'. Choices: {list(RACE_JOB_MAP.keys())}")

    title = RACE_TITLES[norm_race]
    job_keys = RACE_JOB_MAP[norm_race]
    out_sav_name = f"Final Fantasy Tactics Advance ({title}).sav"
    out_gba_name = f"Final Fantasy Tactics Advance ({title}).gba"
    out_sav_path = os.path.join(output_dir, out_sav_name)
    out_gba_path = os.path.join(output_dir, out_gba_name)

    print(f"\n{'=' * 78}")
    print(f"GENERATING FLEET: {title.upper()} ({len(job_keys)} Jobs)")
    print(f"Save Target: {out_sav_path}")
    print(f"ROM Target:  {out_gba_path}")
    print(f"{'=' * 78}")

    # 1. Ensure ROM exists
    if not os.path.exists(out_gba_path):
        if os.path.exists(base_rom_path):
            print(f"[+] Creating ROM: {out_gba_name} (from base)")
            shutil.copy2(base_rom_path, out_gba_path)
        else:
            print(f"[-] Base ROM not found at {base_rom_path}")

    # 2. Load base save
    with open(base_sav_path, "rb") as f:
        sav_data = bytearray(f.read())

    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in base save!")

    info = slots[target_slot]
    sec0_off = info["sectors"][0] * SECTOR_SIZE

    # 3. Configure Marche (Unit 0)
    print("\n[*] Configuring Marche (Unit 0)...")
    setup_marche(sav_data, sec0_off)

    # 4. Configure Montblanc (Unit 1)
    print("[*] Configuring Montblanc (Unit 1)...")
    setup_montblanc(sav_data, sec0_off)

    # 5. Inject race units into slots 2 .. (2 + len(job_keys) - 1)
    print(f"\n[*] Injecting {len(job_keys)} {title} recruits into Slot {target_slot + 1}...")
    for idx, job_key in enumerate(job_keys):
        unit_slot = 2 + idx
        sav_data, summary = inject_unit(
            sav_data,
            build_or_job=job_key,
            target_slot=target_slot,
            target_unit=unit_slot,
            level=level,
            builds_path=BUILDS_PATH,
        )

    # 6. Clear trailing unit slots (slots 2 + len(job_keys) to 23)
    total_active = 2 + len(job_keys)
    print(f"\n[*] Clearing {24 - total_active} trailing clan slots (Unit {total_active}..23)...")
    for u in range(total_active, 24):
        clear_unit_slot(sav_data, sec0_off, u)

    # 6.5 Populate Monster Bank with all 20 monsters
    print("\n[*] Populating Cyril Monster Bank with all 20 monsters...")
    inject_monster_bank(sav_data, target_slot=target_slot, bump_counter=False)

    # 7. Update sequence counter and compute CRC32
    hdr_sec = info["sectors"][0]
    hdr_off = hdr_sec * SECTOR_SIZE
    new_counter = max(info["counter"] + 1, 125)
    sav_data[hdr_off + 8 : hdr_off + 12] = struct.pack("<I", new_counter)

    crc = compute_crc(sav_data, info["sectors"])
    sav_data[hdr_off + 0x0C : hdr_off + 0x10] = struct.pack("<I", crc)
    print(f"[+] Slot {target_slot + 1} counter set to {new_counter}, CRC: {hex(crc)}")

    # 8. Atomic write to destination
    atomic_write(out_sav_path, sav_data)
    print(f"[+] Save written successfully to {out_sav_path}")

    # 9. Validate save
    validate_save_file(out_sav_path, verbose=False)

    # 10. Sync to Pocket if requested
    if sync:
        print("\n[*] Synchronizing with Analogue Pocket SD card...")
        sync_pocket()

    return out_sav_path, out_gba_path


def main():
    parser = argparse.ArgumentParser(description="FFTA Race Save File & Fleet Generator")
    parser.add_argument("race", help="Target race: Hume, Bangaa, Moogle, Viera, Nu Mou, or 'all'")
    parser.add_argument("--base-sav", default=DEFAULT_BASE_SAV, help="Path to base .sav file")
    parser.add_argument("--base-rom", default=DEFAULT_BASE_ROM, help="Path to base .gba ROM")
    parser.add_argument("--output-dir", default=DEFAULT_ASSET_DIR, help="Destination directory for saves/ROMs")
    parser.add_argument("--level", type=int, default=8, help="Recruit unit level (default: 8)")
    parser.add_argument("--sync", action="store_true", help="Sync to Analogue Pocket SD card after generation")
    args = parser.parse_args()

    races_to_generate = []
    if args.race.lower() == "all":
        races_to_generate = list(RACE_JOB_MAP.keys())
    else:
        norm = args.race.lower().replace(" ", "_").replace("-", "_")
        if norm not in RACE_JOB_MAP:
            print(f"[-] Invalid race '{args.race}'. Choose from: {list(RACE_JOB_MAP.keys())} or 'all'")
            sys.exit(1)
        races_to_generate.append(norm)

    for r in races_to_generate:
        generate_race_fleet(
            race_key=r,
            base_sav_path=args.base_sav,
            base_rom_path=args.base_rom,
            output_dir=args.output_dir,
            level=args.level,
            sync=False,
        )

    if args.sync:
        print("\n[*] Performing final sync to Pocket SD card...")
        sync_pocket()


if __name__ == "__main__":
    main()
