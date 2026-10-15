"""Clan roster inspection and diagnostics for FFTA save files."""

import struct

try:
    from mappings import (
        JOB_NAMES,
        KNOWN_ITEMS,
        RACE_ABILITY_SPECS,
        RACE_JOB_COUNTERS,
        RACE_NAMES,
        get_unit_name,
    )
except ImportError:
    from ..mappings import (
        JOB_NAMES,
        KNOWN_ITEMS,
        RACE_ABILITY_SPECS,
        RACE_JOB_COUNTERS,
        RACE_NAMES,
        get_unit_name,
    )

from .save import SECTOR_SIZE, get_slots


def get_item_name(item_id: int) -> str:
    """Returns the English name for an item ID or a fallback hex tag."""
    if item_id == 0:
        return "-"
    return KNOWN_ITEMS.get(item_id, f"Item#{item_id:04x}")


def inspect_save(sav_data: bytearray | bytes, show_roster: bool = True):
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


def display_roster(sav_data: bytearray | bytes, slot_info: dict):
    """Displays formatted ASCII table of all recruited units in the slot."""
    hdr_sec = slot_info["sectors"][0]
    sec0 = sav_data[hdr_sec * SECTOR_SIZE : (hdr_sec + 1) * SECTOR_SIZE]

    units = []
    for u in range(24):
        u_off = 0x80 + u * 0x108
        if u_off + 0x108 > len(sec0):
            break
        ub = sec0[u_off : u_off + 0x108]
        name_id = struct.unpack("<H", ub[0x00:0x02])[0]
        special_flag = ub[0x04]
        race_id = ub[0x06]
        job_id = ub[0x07]
        level = ub[0x09]

        if level > 0 and race_id in RACE_NAMES:
            race = RACE_NAMES[race_id]
            job_name = JOB_NAMES.get(job_id, (f"Job#{job_id:02x}", race))[0]
            unit_name = get_unit_name(name_id, special_flag=special_flag)

            # Abilities count (mastered abilities have bit 7 set in vanilla saves)
            spec = RACE_ABILITY_SPECS.get(race_id, (80, 0, False))
            max_ab = spec[0]
            learned = sum(1 for b in ub[0x41 : 0x41 + max_ab] if (b & 0x80) != 0)

            # Advanced jobs unlocked check
            counters = ub[0xF1:0x106]
            is_unlocked = counters == RACE_JOB_COUNTERS.get(race_id, b"") or (learned > 0 and learned == max_ab)

            # Equipment
            gear_ids = struct.unpack("<5H", ub[0x2A:0x34])
            w1, w2 = gear_ids[0], gear_ids[1]
            eq_str = f"{get_item_name(w1)} / {get_item_name(w2)}"
            if 0x015C in gear_ids and w1 != 0x015C and w2 != 0x015C:
                eq_str += " [Tabi]"
            if 0x0114 in gear_ids and w1 != 0x0114 and w2 != 0x0114:
                eq_str += " [Ribbon]"

            red_cards = ub[0x102]
            yellow_cards = ub[0x103]
            if red_cards > 0 or yellow_cards > 0:
                card_strs = []
                if yellow_cards > 0:
                    card_strs.append(f"{yellow_cards}Y")
                if red_cards > 0:
                    card_strs.append(f"{red_cards}R")
                eq_str += f" [Cards: {'/'.join(card_strs)}]"

            if (ub[0x28] & 0x08) != 0:
                eq_str += " [Jailed]"

            units.append(
                {
                    "idx": u,
                    "name": unit_name,
                    "race": race,
                    "job": job_name,
                    "level": level,
                    "learned": f"{learned}/{max_ab}",
                    "unlocked": "YES" if is_unlocked else "NO",
                    "gear": eq_str,
                }
            )

    if not units:
        print("      No active clan members found.")
        return

    print("\n      CLAN ROSTER:")
    print("      +----+-----------+---------+--------------+-----+---------+----------+----------------------------+")
    print("      | #  | Name      | Race    | Current Job  | Lv  | Skills  | Adv Jobs | Main Weapons / Key Items   |")
    print("      +----+-----------+---------+--------------+-----+---------+----------+----------------------------+")
    for u in units:
        print(
            f"      | {u['idx']:<2} | {u['name']:<9} | {u['race']:<7} | {u['job']:<12} | "
            f"{u['level']:<3} | {u['learned']:<7} | {u['unlocked']:<8} | "
            f"{u['gear']:<26} |"
        )
    print("      +----+-----------+---------+--------------+-----+---------+----------+----------------------------+")
