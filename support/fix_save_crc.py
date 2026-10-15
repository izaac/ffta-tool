#!/usr/bin/env python3
"""FFTA Save File Checksum Repair Tool.

Quick CLI utility to recalculate and repair CRC32 checksums across wear-leveled
save slots without modifying unit data or inventory.
"""

import argparse
import os
import struct
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.save import SECTOR_SIZE, atomic_write, get_slots


def fix_file_crc(path: str) -> bool:
    """Repairs CRC32 checksums for both slots in an FFTA save file."""
    if not os.path.exists(path):
        print(f"[-] File not found: {path}")
        return False

    with open(path, "rb") as f:
        data = bytearray(f.read())

    slots = get_slots(data)
    modified = False

    print(f"\n[*] Inspecting CRCs for {os.path.basename(path)}...")
    for slot_idx in [0, 1]:
        info = slots.get(slot_idx)
        if not info:
            continue

        stored = info["stored_crc"]
        computed = info.get("calc_crc", info.get("computed_crc", 0))
        hdr_sec = info["sectors"][0]
        hdr_off = hdr_sec * SECTOR_SIZE

        if stored != computed:
            print(f"  [!] Slot {slot_idx + 1}: CRC mismatch! Stored {hex(stored)} -> Repairing to {hex(computed)}")
            data[hdr_off + 0x0C : hdr_off + 0x10] = struct.pack("<I", computed)
            modified = True
        else:
            print(f"  [=] Slot {slot_idx + 1}: CRC valid ({hex(stored)})")

    if modified:
        atomic_write(path, data)
        print(f"[+] Successfully repaired and saved {os.path.basename(path)}")
    else:
        print("[+] All slots already have valid CRC32 checksums.")

    return True


def main():
    parser = argparse.ArgumentParser(description="Repair FFTA save file CRC32 checksums")
    parser.add_argument("path", help="Path to .sav file to repair")
    args = parser.parse_args()

    fix_file_crc(args.path)


if __name__ == "__main__":
    main()
