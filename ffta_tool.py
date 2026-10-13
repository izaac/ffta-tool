#!/usr/bin/env python3
"""
Final Fantasy Tactics Advance (GBA) - Ultimate Save Tool & Clan Manager
========================================================================

A hardened, battle-tested utility for inspecting, managing, and patching
Final Fantasy Tactics Advance (GBA) Flash 64K / 128K wear-leveled save files.

Features:
 - Auto-detection of live NextUI SD card saves and local backups.
 - Automatic timestamped snapshot backups before any write operation.
 - Full wear-leveling sector resolution and IEEE 802.3 CRC32 verification.
 - Rich ASCII Clan Roster Inspector (jobs, levels, equipment, abilities, unlock status).
 - Recruits / Clan Patcher: Masters all abilities and un-gates advanced jobs in Job menu.
 - Super Starter Patcher: 10x 361 endgame equipment, 99x consumables, clean Cyril pub state.
 - Atomic file replacement with filesystem sync to prevent corruption.
"""

import os
import sys
import glob
import zlib
import struct
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# ==============================================================================
# Constants & Formats
# ==============================================================================

SECTOR_SIZE = 0x1000
MAGIC = b"FFTEX000"


def get_default_backup_dir() -> Path:
    """Returns the backup directory path without using tilde expansion."""
    home = os.environ.get("HOME")
    if home:
        return Path(home) / "Documents" / "FFTA_Backups"
    return Path.cwd() / "backups"


# Races
RACE_NAMES = {
    1: "Hume",
    2: "Bangaa",
    3: "Nu Mou",
    4: "Viera",
    5: "Moogle",
}

# Jobs (Hex ID -> (Job Name, Race))
JOB_NAMES = {
    # Hume (0x01..0x0C)
    0x01: ("Soldier", "Hume"),
    0x02: ("Paladin", "Hume"),
    0x03: ("Paladin", "Hume"),
    0x04: ("Fighter", "Hume"),
    0x05: ("Thief", "Hume"),
    0x06: ("Ninja", "Hume"),
    0x07: ("White Mage", "Hume"),
    0x08: ("Black Mage", "Hume"),
    0x09: ("Illusionist", "Hume"),
    0x0A: ("Blue Mage", "Hume"),
    0x0B: ("Archer", "Hume"),
    0x0C: ("Hunter", "Hume"),

    # Bangaa (0x0D..0x13)
    0x0D: ("Warrior", "Bangaa"),
    0x0E: ("White Monk", "Bangaa"),
    0x0F: ("Dragoon", "Bangaa"),
    0x10: ("Gladiator", "Bangaa"),
    0x11: ("Defender", "Bangaa"),
    0x12: ("Bishop", "Bangaa"),
    0x13: ("Templar", "Bangaa"),

    # Nu Mou (0x14..0x1B)
    0x14: ("White Mage", "Nu Mou"),
    0x15: ("Black Mage", "Nu Mou"),
    0x16: ("Time Mage", "Nu Mou"),
    0x17: ("Illusionist", "Nu Mou"),
    0x18: ("Alchemist", "Nu Mou"),
    0x19: ("Beastmaster", "Nu Mou"),
    0x1A: ("Morpher", "Nu Mou"),
    0x1B: ("Sage", "Nu Mou"),

    # Viera (0x1C..0x23)
    0x1C: ("Fencer", "Viera"),
    0x1D: ("Elementalist", "Viera"),
    0x1E: ("Red Mage", "Viera"),
    0x1F: ("White Mage", "Viera"),
    0x20: ("Summoner", "Viera"),
    0x21: ("Archer", "Viera"),
    0x22: ("Assassin", "Viera"),
    0x23: ("Sniper", "Viera"),

    # Moogle (0x24..0x2B)
    0x24: ("Animist", "Moogle"),
    0x25: ("Mog Knight", "Moogle"),
    0x26: ("Gunner", "Moogle"),
    0x27: ("Thief", "Moogle"),
    0x28: ("Juggler", "Moogle"),
    0x29: ("Gadgeteer", "Moogle"),
    0x2A: ("Black Mage", "Moogle"),
    0x2B: ("Time Mage", "Moogle"),
}

# Known signature items for visualizer
KNOWN_ITEMS = {
    0x0001: "Shortsword",
    0x0002: "Silver Sword",
    0x0003: "Buster Sword",
    0x0004: "Burglar Sword",
    0x0005: "Gale Sword",
    0x0006: "Blood Sword",
    0x0008: "Restorer",
    0x0009: "Mythril Sword",
    0x0012: "Flametongue",
    0x001A: "Materia Blade",
    0x001E: "Ayvuir Red",
    0x001F: "Ayvuir Blue",
    0x0020: "Blue Saber",
    0x0026: "Tulwar",
    0x0028: "Defender",
    0x0029: "Apocalypse",
    0x002A: "Lion Heart",
    0x002B: "Ragnarok",
    0x0030: "Mythril Brand",
    0x0031: "Excalibur",
    0x0032: "Nagrarok",
    0x0033: "Sequence",
    0x004C: "Khukuri",
    0x004E: "Scramasax",
    0x0056: "Mythril Knife",
    0x0057: "Tonberrian",
    0x0058: "Tiptaptwo",
    0x005C: "Flamberge",
    0x0073: "Masamune",
    0x0076: "Masamune 100",
    0x0085: "Power Staff",
    0x0086: "Dream Watcher",
    0x0087: "Rod",
    0x0088: "Firewheel Rod",
    0x009C: "Lotus Mace",
    0x009E: "Scorpion Tail",
    0x009F: "Zeus Mace",
    0x00A2: "Longbow",
    0x00B5: "Nike Bow",
    0x00B8: "Seventh Heaven",
    0x00C2: "Partisan",
    0x00CC: "Conch Shell",
    0x00CF: "Silver Bow",
    0x00D7: "Hard Knuckles",
    0x00DB: "Kaiser Knuckles",
    0x00F5: "Lost Gun",
    0x00F6: "Peacemaker",
    0x00F7: "Giot Gun",
    0x00FD: "Bronze Shield",
    0x00FE: "Round Shield",
    0x00FF: "Opal Shield",
    0x0100: "Ice Shield",
    0x0101: "Flame Shield",
    0x0102: "Aegis Shield",
    0x0103: "Genji Shield",
    0x0104: "Sacri Shield",
    0x0105: "Shijin Shield",
    0x0106: "Chocobo Shield",
    0x0107: "La Seraphica",
    0x0108: "Reverie Shield",
    0x0109: "Bronze Helmet",
    0x010A: "Iron Helmet",
    0x010B: "Opal Helmet",
    0x010C: "Cross Helmet",
    0x010D: "Diamond Helmet",
    0x010E: "Genji Helmet",
    0x010F: "Parade Helmet",
    0x0110: "Hanya Helmet",
    0x0111: "Bangaa Helmet",
    0x0112: "Cachusha",
    0x0113: "Barette",
    0x0114: "Ribbon",
    0x0115: "Feather Cap",
    0x0116: "Circlet",
    0x0117: "Green Beret",
    0x0118: "Headband",
    0x0119: "Wizard Hat",
    0x011A: "Gold Hairpin",
    0x011B: "Thief Hat",
    0x011C: "Black Hat",
    0x011D: "White Hat",
    0x011E: "Acacia Hat",
    0x011F: "Tiara",
    0x0120: "Cuirass",
    0x0121: "Bronze Armor",
    0x0122: "Iron Armor",
    0x0123: "Platemail",
    0x0124: "Gold Armor",
    0x0130: "Chain Plate",
    0x0131: "Adaman Vest",
    0x0132: "Survival Vest",
    0x0133: "Brigandine",
    0x0137: "Minerva Plate",
    0x0138: "Ninja Gear",
    0x0139: "Dark Gear",
    0x0147: "Blaze Robe",
    0x014B: "Black Robe",
    0x014C: "Light Robe",
    0x014D: "Lordly Robe",
    0x0153: "Battle Boots",
    0x0154: "Spiked Boots",
    0x0155: "Dash Boots",
    0x015A: "Fairy Shoes",
    0x015C: "Ninja Tabi",
    0x015D: "Gauntlets",
    0x0163: "Fortune Ring",
    0x0165: "Angel Ring",
    0x0169: "Mindu Gem",
}

# Race ability counts starting at unit + 0x41
RACE_ABILITY_SPECS = {
    1: (140, 26, False),  # Hume: count, blue_magic, morpher
    2: (76, 0, False),    # Bangaa
    3: (94, 0, True),     # Nu Mou: + morpher
    4: (84, 0, False),    # Viera
    5: (87, 0, False),    # Moogle
}

# Cache byte array at unit + 0xF1..0x106 used by the Job change menu
RACE_JOB_COUNTERS = {
    1: bytes.fromhex("ff 0c 00 00 00 02 05 02 02 05 06 01 02 03 fc 00 02 00 03 02 00"),
    2: bytes.fromhex("0e 02 00 00 00 0a 07 01 00 00 09 01 02 02 fd 00 01 00 00 03 00"),
    3: bytes.fromhex("6b 18 00 00 00 07 02 01 00 00 0a 01 02 04 fb 00 01 00 00 01 00"),
    4: bytes.fromhex("ff 10 00 00 00 07 07 03 00 00 0b 01 02 04 fb 00 02 00 01 00 00"),
    5: bytes.fromhex("37 07 00 00 00 0a 02 01 04 01 07 01 02 02 fd 00 01 00 02 05 00"),
}

EQUIPMENT_IDS = list(range(1, 0x16A))
CONSUMABLE_IDS = list(range(0x16A, 0x178))


# ==============================================================================
# Save File Operations & CRC32
# ==============================================================================

def compute_crc(sav_data, sectors):
    """Calculates internal FFTA IEEE 802.3 CRC32 checksum over 0x2FC4 buffer."""
    buf = bytearray()
    for s in sectors:
        buf.extend(sav_data[s * SECTOR_SIZE : (s + 1) * SECTOR_SIZE])
    buf[0x0C:0x10] = b"\x00" * 4
    buf[0x12:0x17] = b"\x00" * 5
    return zlib.crc32(buf[:0x2FC4]) & 0xFFFFFFFF


def get_slots(sav_data):
    """Detects active Slot 1 and Slot 2 headers across 16 flash sectors."""
    slots = {}
    total_sectors = len(sav_data) // SECTOR_SIZE
    for s in range(min(16, total_sectors)):
        hdr = sav_data[s * SECTOR_SIZE : (s + 1) * SECTOR_SIZE]
        if hdr[:8] == MAGIC:
            slot_id = hdr[0x10]
            counter = struct.unpack("<I", hdr[8:12])[0]
            missions = struct.unpack("<H", hdr[0x76:0x78])[0]
            secs = list(hdr[0x12:0x16])
            stored_crc = struct.unpack("<I", hdr[0x0C:0x10])[0]
            calc_crc = compute_crc(sav_data, secs)

            entry = {
                "header_sector": s,
                "counter": counter,
                "missions": missions,
                "sectors": secs,
                "stored_crc": stored_crc,
                "calc_crc": calc_crc,
                "valid": stored_crc == calc_crc,
            }

            if slot_id not in slots or counter > slots[slot_id]["counter"]:
                slots[slot_id] = entry

    return slots


def auto_detect_save():
    """Attempts to find the most relevant FFTA save file automatically."""
    candidates = []

    # Check removable media mounts dynamically across system mount points
    for mount_root in ["/run/media", "/media", "/mnt"]:
        pattern = f"{mount_root}/*/*/Saves/GBA/*Final Fantasy Tactics Advance*.sav"
        candidates.extend(glob.glob(pattern))

    home = os.environ.get("HOME")
    if home:
        home_path = Path(home)
        doc_dir = home_path / "Documents"
        backup_dir = doc_dir / "FFTA_Backups"
        candidates.extend([
            str(doc_dir / "FFTA_Save_Slot2_Mastered_Recruits_Juggler.sav"),
            str(backup_dir / "FFTA_Save_Slot2_Mastered_Recruits_Juggler.sav"),
            str(backup_dir / "Final_Fantasy_Tactics_Advance_Current_Patched.sav"),
        ])
        if backup_dir.is_dir():
            candidates.extend(glob.glob(str(backup_dir / "*.sav")))

    # Fallback to current directory .sav files
    candidates.extend(glob.glob("*.sav"))

    for p in candidates:
        if os.path.isfile(p) and os.path.getsize(p) >= 0x10000:
            return p

    return None


def create_snapshot_backup(filepath, action_name="update"):
    """Creates a timestamped snapshot in the backups directory before writing."""
    backup_dir = get_default_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    clean_base = base_name.replace("Final Fantasy Tactics Advance (USA, Australia).zip", "FFTA")
    backup_filename = f"{clean_base}_{action_name}_{ts}.sav"
    backup_path = str(backup_dir / backup_filename)
    shutil.copy2(filepath, backup_path)
    return backup_path


def atomic_write(filepath, data):
    """Safely writes data to a temporary file then replaces target atomically."""
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)
    try:
        os.sync()
    except AttributeError:
        pass


# ==============================================================================
# Clan Roster Inspector
# ==============================================================================

def get_item_name(item_id):
    if item_id == 0:
        return "-"
    return KNOWN_ITEMS.get(item_id, f"Item#{item_id:04x}")


def inspect_save(sav_data, show_roster=True):
    """Displays save diagnostic, wear-leveling details, and clan roster."""
    slots = get_slots(sav_data)
    print("=" * 78)
    print("  FINAL FANTASY TACTICS ADVANCE (GBA) - SAVE DIAGNOSTIC")
    print("=" * 78)
    if not slots:
        print("  [-] No valid FFTA save slots detected!")
        print("=" * 78)
        return

    for slot_id, info in sorted(slots.items()):
        name = f"Slot {slot_id + 1}"
        status = "VALID" if info["valid"] else "INVALID CHECKSUM"
        status_sym = "[OK]" if info["valid"] else "[ERR]"
        print(f"\n  {status_sym} {name} (Flash Sector {info['header_sector']})")
        print(f"      Sequence Counter: {info['counter']}")
        print(f"      Sectors (0..3):   {info['sectors']}")
        print(f"      Missions Cleared: {info['missions']}")
        print(f"      Stored CRC32:     {hex(info['stored_crc'])} ({status})")

        if show_roster:
            display_roster(sav_data, info)

    print("\n" + "=" * 78)


def display_roster(sav_data, slot_info):
    """Displays formatted ASCII table of all recruited units in the slot."""
    hdr_sec = slot_info["sectors"][0]
    sec0 = sav_data[hdr_sec * SECTOR_SIZE : (hdr_sec + 1) * SECTOR_SIZE]

    units = []
    for u in range(24):
        u_off = 0x80 + u * 0x108
        if u_off + 0x108 > len(sec0):
            break
        ub = sec0[u_off : u_off + 0x108]
        race_id = ub[0x06]
        job_id = ub[0x07]
        level = ub[0x09]

        # Let's inspect race & job accurately
        if level > 0 and race_id in RACE_NAMES:
            race = RACE_NAMES[race_id]
            job_name = JOB_NAMES.get(job_id, (f"Job#{job_id:02x}", race))[0]

            # Abilities count
            spec = RACE_ABILITY_SPECS.get(race_id, (80, 0, False))
            max_ab = spec[0]
            learned = sum(1 for b in ub[0x41 : 0x41 + max_ab] if b == 0xE4)

            # Advanced jobs unlocked check
            counters = ub[0xF1:0x106]
            is_unlocked = any(counters)

            # Equipment
            gear_ids = struct.unpack("<5H", ub[0x2A:0x34])
            w1, w2 = gear_ids[0], gear_ids[1]
            eq_str = f"{get_item_name(w1)} / {get_item_name(w2)}"
            if 0x015C in gear_ids and w1 != 0x015C and w2 != 0x015C:
                eq_str += " [Tabi]"
            if 0x0114 in gear_ids and w1 != 0x0114 and w2 != 0x0114:
                eq_str += " [Ribbon]"

            units.append({
                "idx": u,
                "race": race,
                "job": job_name,
                "level": level,
                "learned": f"{learned}/{max_ab}",
                "unlocked": "YES" if is_unlocked else "NO",
                "gear": eq_str,
            })

    if not units:
        print("      No active clan members found.")
        return

    print("\n      CLAN ROSTER:")
    print("      +----+---------+--------------+-----+---------+----------+----------------------------+")
    print("      | #  | Race    | Current Job  | Lv  | Skills  | Adv Jobs | Main Weapons / Key Items   |")
    print("      +----+---------+--------------+-----+---------+----------+----------------------------+")
    for u in units:
        print(f"      | {u['idx']:<2} | {u['race']:<7} | {u['job']:<12} | {u['level']:<3} | {u['learned']:<7} | {u['unlocked']:<8} | {u['gear']:<26} |")
    print("      +----+---------+--------------+-----+---------+----------+----------------------------+")


# ==============================================================================
# Patching Functions
# ==============================================================================

def patch_clan_units(sav_data, target_slot=1, target_unit=None):
    """Masters abilities and unlocks advanced jobs for recruited clan units."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]
    hdr_offset = hdr_sec * SECTOR_SIZE

    patched_count = 0
    units_to_patch = [target_unit] if target_unit is not None else list(range(24))

    for u in units_to_patch:
        u_addr = hdr_offset + 0x80 + u * 0x108
        if u_addr + 0x108 > len(sav_data):
            break

        race_id = sav_data[u_addr + 0x06]
        level = sav_data[u_addr + 0x09]

        if level > 0 and race_id in RACE_ABILITY_SPECS:
            count, blue_magic, morpher = RACE_ABILITY_SPECS[race_id]
            race_name = RACE_NAMES.get(race_id, "Unknown")

            # Check if unit is already fully patched
            already_abilities = all(sav_data[u_addr + 0x41 + i] == 0xE4 for i in range(count))
            already_jobs = sav_data[u_addr + 0xF1 : u_addr + 0x106] == RACE_JOB_COUNTERS.get(race_id, b"")
            if already_abilities and already_jobs:
                print(f"  [-] Unit {u} ({race_name}, Lv {level}): Already fully patched, skipping.")
                continue

            # Master abilities
            for i in range(count):
                sav_data[u_addr + 0x41 + i] = 0xE4
            if blue_magic:
                for i in range(blue_magic):
                    sav_data[u_addr + 0x9C + i] = 0xE4
            if morpher:
                for i in range(12):
                    sav_data[u_addr + 0x93 + i] = 0xE4

            # Inject advanced job unlock cache counters
            if race_id in RACE_JOB_COUNTERS:
                sav_data[u_addr + 0xF1 : u_addr + 0x106] = RACE_JOB_COUNTERS[race_id]

            print(f"  [+] Unit {u} ({race_name}, Lv {level}): Mastered all {count} skills + unlocked advanced jobs.")
            patched_count += 1

    # Bump wear-leveling sequence counter
    new_counter = info["counter"] + 1
    sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)

    # Recompute CRC32
    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)

    print(f"\n  [+] Successfully patched {patched_count} clan units.")
    print(f"  [+] Sequence counter incremented to: {new_counter}")
    print(f"  [+] Checksum updated: {hex(new_crc)}")
    return sav_data


def patch_super_starter(sav_data, target_slot=1, equip_qty=10, item_qty=99, counter_bump=50):
    """Applies the complete Super Starter patch to the specified slot."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in save file!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec, sec1 = secs[0], secs[1]
    hdr_offset = hdr_sec * SECTOR_SIZE

    print(f"[*] Applying Super Starter patch to Slot {target_slot + 1}...")

    # 1. Bump save sequence counter
    new_counter = max(info["counter"] + 1, counter_bump)
    sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)

    # 2. Reset missions cleared counter
    sav_data[hdr_offset + 0x76 : hdr_offset + 0x78] = b"\x00\x00"

    # 3. Master abilities and unlock jobs for all units
    patch_clan_units(sav_data, target_slot=target_slot)

    # 4. Inject equipment and consumables into Sector 1
    sec1_offset = sec1 * SECTOR_SIZE
    orig_flags = {}
    for i in range(0x940, 0xEE4, 4):
        addr = sec1_offset + i
        iid = int.from_bytes(sav_data[addr:addr+2], "little")
        if iid != 0:
            orig_flags[iid] = sav_data[addr + 3]

    for idx, eid in enumerate(EQUIPMENT_IDS):
        addr = sec1_offset + 0x940 + idx * 4
        sav_data[addr:addr+2] = eid.to_bytes(2, "little")
        sav_data[addr+2] = equip_qty
        sav_data[addr+3] = orig_flags.get(eid, 0)

    for idx, cid in enumerate(CONSUMABLE_IDS):
        addr = sec1_offset + 0xEE4 + idx * 4
        sav_data[addr:addr+2] = cid.to_bytes(2, "little")
        sav_data[addr+2] = item_qty
        sav_data[addr+3] = 0

    print(f"  [+] Injected {len(EQUIPMENT_IDS)} weapons/gear ({equip_qty}x) and {len(CONSUMABLE_IDS)} consumables ({item_qty}x).")

    # 5. Recalculate CRC32
    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)
    print(f"  [+] Super Starter complete. Checksum: {hex(new_crc)}")
    return sav_data


def fix_crc(sav_data, target_slot=1):
    """Recalculates and updates CRC32 for a specific slot."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]

    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_sec * SECTOR_SIZE + 0x0C : hdr_sec * SECTOR_SIZE + 0x10] = struct.pack("<I", new_crc)
    print(f"  [+] Slot {target_slot + 1} CRC updated to: {hex(new_crc)}")
    return sav_data


# ==============================================================================
# CLI Entry Point
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Final Fantasy Tactics Advance (GBA) - Save Tool & Clan Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                # Auto-detect save and show clan roster
  %(prog)s --inspect                      # Full diagnostic on default/detected save
  %(prog)s --patch-units                  # Master all skills & unlock jobs for clan
  %(prog)s --patch-units --unit 7         # Target specific recruit (e.g. unit 7)
  %(prog)s --backup                       # Create an instant snapshot backup
  %(prog)s --super-starter                # Apply complete Super Starter package
  %(prog)s --fix-crc                      # Recalculate and repair CRC32 checksum
        """,
    )
    parser.add_argument("save_file", nargs="?", help="Path to FFTA save file (.sav). Auto-detected if omitted.")
    parser.add_argument("-i", "--inspect", action="store_true", help="Display full save diagnostic & clan roster")
    parser.add_argument("-p", "--patch-units", action="store_true", help="Master skills & unlock advanced jobs for recruits")
    parser.add_argument("-u", "--unit", type=int, help="Target specific unit index (0..23) for patching")
    parser.add_argument("-s", "--super-starter", action="store_true", help="Apply complete Super Starter patch")
    parser.add_argument("-b", "--backup", action="store_true", help="Create a timestamped snapshot backup without changes")
    parser.add_argument("--fix-crc", action="store_true", help="Recalculate and write valid CRC checksum")
    parser.add_argument("--slot", type=int, default=2, choices=[1, 2], help="Target save slot (1 or 2, default: 2)")
    parser.add_argument("--equip-qty", type=int, default=10, help="Equipment quantity for Super Starter (default: 10)")
    parser.add_argument("--item-qty", type=int, default=99, help="Consumable quantity for Super Starter (default: 99)")
    parser.add_argument("--no-backup", action="store_true", help="Disable automatic pre-patch snapshot backups")
    parser.add_argument("-o", "--output", help="Output path (default: overwrite input file atomically)")

    args = parser.parse_args()

    # Save file resolution
    target_path = args.save_file
    if not target_path:
        target_path = auto_detect_save()
        if target_path:
            print(f"[*] Auto-detected save: {target_path}")
        else:
            print("Error: No save file specified and none found in common paths.", file=sys.stderr)
            sys.exit(1)

    if not os.path.exists(target_path):
        print(f"Error: Save file not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    # Standalone backup
    if args.backup:
        b_path = create_snapshot_backup(target_path, "manual_backup")
        print(f"[+] Created snapshot backup: {b_path}")
        return

    with open(target_path, "rb") as f:
        data = bytearray(f.read())

    target_slot = args.slot - 1

    # Default action: Inspect
    is_modifying = args.patch_units or args.super_starter or args.fix_crc
    if not is_modifying or args.inspect:
        inspect_save(data, show_roster=True)
        if not is_modifying:
            return

    # Automatic snapshot backup before modification
    if not args.no_backup:
        action_name = "super_starter" if args.super_starter else "patch_units" if args.patch_units else "crc_fix"
        b_path = create_snapshot_backup(target_path, action_name)
        print(f"[*] Created pre-patch snapshot backup: {b_path}")

    # Modifications
    if args.patch_units:
        data = patch_clan_units(data, target_slot=target_slot, target_unit=args.unit)

    if args.super_starter:
        data = patch_super_starter(
            data,
            target_slot=target_slot,
            equip_qty=args.equip_qty,
            item_qty=args.item_qty,
        )

    if args.fix_crc and not args.patch_units and not args.super_starter:
        data = fix_crc(data, target_slot=target_slot)

    # Atomic write
    out_path = args.output if args.output else target_path
    atomic_write(out_path, data)
    print(f"\n[+] Successfully saved to: {out_path}")
    print("\n[!] NOTE: Ensure game is closed / restarted on NextUI handheld to reload save!")


if __name__ == "__main__":
    main()
