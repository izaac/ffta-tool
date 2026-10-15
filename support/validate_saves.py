#!/usr/bin/env python3
"""FFTA Save File Diagnostic and Validation Tool.

Validates save slot headers, CRC32 checksums, sequence counters, unit stats,
equipment loadouts, and checks for duplicate primary/secondary skills or sprite bugs.
"""

import argparse
import os
import struct
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.save import SECTOR_SIZE, get_slots
from mappings import JOB_NAMES, KNOWN_ITEMS, get_unit_name
from support.sync_pocket import DEFAULT_ASSET_DIR, DEFAULT_POCKET_BASE

DEFAULT_POCKET_DIR = os.path.join(DEFAULT_POCKET_BASE, "Saves/gba")


def validate_save_file(path: str, verbose: bool = True) -> bool:
    """Inspects a single FFTA save file and prints a formatted diagnostic report."""
    if not os.path.exists(path):
        print(f"[-] File not found: {path}")
        return False

    with open(path, "rb") as f:
        data = f.read()

    slots = get_slots(data)
    fname = os.path.basename(path)
    print(f"\n{'=' * 78}")
    print(f"FILE: {fname}")
    print(f"PATH: {path} ({len(data)} bytes)")
    print(f"{'=' * 78}")

    file_clean = True
    for slot_idx in [0, 1]:
        info = slots.get(slot_idx)
        if not info:
            continue

        status = "VALID" if info["valid"] else "INVALID CRC"
        crc_str = hex(info["stored_crc"])
        counter = info["counter"]
        print(f"\n--- Slot {slot_idx + 1} ({status}) | Counter: {counter} | CRC: {crc_str} ---")

        if not info["valid"]:
            file_clean = False
            calc_crc = info.get("calc_crc", info.get("computed_crc", 0))
            print(f"  [!] Checksum mismatch: Stored {crc_str} != Computed {hex(calc_crc)}")

        sec0_off = info["sectors"][0] * SECTOR_SIZE
        sec0 = data[sec0_off : sec0_off + SECTOR_SIZE]

        active_units = 0
        for u in range(24):
            u_off = 0x80 + u * 0x108
            if u_off + 0x108 > len(sec0):
                break

            ub = sec0[u_off : u_off + 0x108]
            lvl = ub[0x09]
            if lvl == 0:
                continue

            active_units += 1
            nid = struct.unpack("<H", ub[0:2])[0]
            flag = ub[0x04]
            b5 = ub[0x05]
            p_job = ub[0x07]
            s_job = ub[0x08]
            p_set = ub[0x35]
            s_set = ub[0x36]
            spd = struct.unpack("<H", ub[0xD2:0xD4])[0]
            gear_raw = struct.unpack("<5H", ub[0x2A:0x34])
            gear_names = [KNOWN_ITEMS.get(g, hex(g)) if g else "-" for g in gear_raw]
            uname = get_unit_name(nid, special_flag=flag)
            pj_name = JOB_NAMES.get(p_job, ("?", ""))[0]
            sj_name = JOB_NAMES.get(s_job, ("?", ""))[0]

            issues = []
            if p_set == s_set or p_job == s_job:
                issues.append("DUPE SKILL!")
                file_clean = False
            if p_job == 2 and b5 == 1:
                issues.append("PROLOGUE SPRITE BUG (B5=1)!")
                file_clean = False

            issue_str = f" *** {', '.join(issues)} ***" if issues else ""

            if verbose:
                print(
                    f"  Unit {u:2d}: {uname:<10} (Lv {lvl:2d} {pj_name:<11} / {sj_name:<11}) "
                    f"Spd:{spd:3d} B5:{b5:2d} | Sets:({p_set:2d}/{s_set:2d}){issue_str}"
                )
                print(f"           Gear: {gear_names}")

        print(f"  Active Clan Units: {active_units} / 24")

    return file_clean


def main():
    parser = argparse.ArgumentParser(description="FFTA Save File Diagnostic Tool")
    parser.add_argument("path", nargs="?", help="Path to specific .sav file to inspect")
    parser.add_argument("--all", action="store_true", help="Validate all saves in FFTA_Assets")
    parser.add_argument("--pocket", action="store_true", help="Validate all saves on Pocket SD card")
    args = parser.parse_args()

    paths_to_check = []
    if args.path:
        paths_to_check.append(args.path)
    elif args.pocket:
        if os.path.exists(DEFAULT_POCKET_DIR):
            for f in sorted(os.listdir(DEFAULT_POCKET_DIR)):
                if f.endswith(".sav"):
                    paths_to_check.append(os.path.join(DEFAULT_POCKET_DIR, f))
        else:
            print(f"[-] Pocket directory not mounted at {DEFAULT_POCKET_DIR}")
            sys.exit(1)
    else:
        # Default: scan FFTA_Assets and Pocket if available
        if os.path.exists(DEFAULT_ASSET_DIR):
            for f in sorted(os.listdir(DEFAULT_ASSET_DIR)):
                if f.endswith(".sav"):
                    paths_to_check.append(os.path.join(DEFAULT_ASSET_DIR, f))
        if os.path.exists(DEFAULT_POCKET_DIR):
            for f in sorted(os.listdir(DEFAULT_POCKET_DIR)):
                if f.endswith(".sav") and f not in [os.path.basename(p) for p in paths_to_check]:
                    paths_to_check.append(os.path.join(DEFAULT_POCKET_DIR, f))

    if not paths_to_check:
        print("[-] No save files found to inspect.")
        sys.exit(1)

    all_passed = True
    for p in paths_to_check:
        clean = validate_save_file(p, verbose=True)
        if not clean:
            all_passed = False

    print(f"\n{'=' * 78}")
    if all_passed:
        print(">>> ALL SAVE FILES ARE 100% VALID AND CLEAN! <<<")
    else:
        print(">>> WARNING: SOME SAVES CONTAIN ANOMALIES (SEE ABOVE) <<<")
    print(f"{'=' * 78}")


if __name__ == "__main__":
    main()
