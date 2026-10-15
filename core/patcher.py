"""Clan unit ability mastering, Super Starter generation, and card clearing."""

import struct

try:
    from mappings import (
        CONSUMABLE_IDS,
        EQUIPMENT_IDS,
        RACE_ABILITY_SPECS,
        RACE_JOB_COUNTERS,
        RACE_NAMES,
    )
except ImportError:
    from ..mappings import (
        CONSUMABLE_IDS,
        EQUIPMENT_IDS,
        RACE_ABILITY_SPECS,
        RACE_JOB_COUNTERS,
        RACE_NAMES,
    )

from .builder import equip_unit_build
from .save import SECTOR_SIZE, compute_crc, get_slots


def patch_clan_units(sav_data: bytearray, target_slot: int = 1, target_unit: int | None = None) -> bytearray:
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
            already_abilities = all((sav_data[u_addr + 0x41 + i] & 0x80) != 0 for i in range(count))
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

            # Clear yellow and red cards and jail status
            sav_data[u_addr + 0x102] = 0
            sav_data[u_addr + 0x103] = 0
            if (sav_data[u_addr + 0x28] & 0x08) != 0:
                sav_data[u_addr + 0x28] &= ~0x08
                sav_data[u_addr + 0x101] = 0x00
                sav_data[u_addr + 0x104] = 0xFF

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


def clear_clan_cards(sav_data: bytearray, target_slot: int = 1, re_equip: bool = True) -> bytearray:
    """Zeroes out all red and yellow cards and pardons jailed units in target slot."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]
    hdr_offset = hdr_sec * SECTOR_SIZE

    cleared = 0
    for u in range(24):
        u_addr = hdr_offset + 0x80 + u * 0x108
        if u_addr + 0x108 > len(sav_data):
            break
        level = sav_data[u_addr + 0x09]
        if level > 0:
            red_cards = sav_data[u_addr + 0x102]
            yellow_cards = sav_data[u_addr + 0x103]
            is_jailed = (sav_data[u_addr + 0x28] & 0x08) != 0
            if red_cards > 0 or yellow_cards > 0 or is_jailed:
                cleared += 1
            sav_data[u_addr + 0x102] = 0  # Red Cards
            sav_data[u_addr + 0x103] = 0  # Yellow Cards
            if is_jailed:
                sav_data[u_addr + 0x28] &= ~0x08  # Clear In-Jail status bit
                sav_data[u_addr + 0x101] = 0x00  # Clear remaining sentence counter
                sav_data[u_addr + 0x104] = 0xFF  # Reset state to free (0xFF)
                if re_equip:
                    cur_gear = struct.unpack("<5H", sav_data[u_addr + 0x2A : u_addr + 0x34])
                    if all(g == 0 for g in cur_gear):
                        equip_unit_build(sav_data, target_slot=target_slot, target_unit=u, bump_counter=False)

    new_counter = info["counter"] + 1
    sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)
    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)

    print(f"  [+] Cleared all cards and pardoned jailed units for {cleared} units.")
    print(f"  [+] Sequence counter incremented to: {new_counter}")
    print(f"  [+] Checksum updated: {hex(new_crc)}")
    return sav_data


def patch_super_starter(
    sav_data: bytearray,
    target_slot: int = 1,
    equip_qty: int = 10,
    item_qty: int = 99,
    counter_bump: int = 50,
    force: bool = False,
) -> bytearray:
    """Applies the complete Super Starter patch to the specified slot."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in save file!")

    info = slots[target_slot]
    if info["missions"] > 0 and not force:
        raise ValueError(
            f"Slot {target_slot + 1} has {info['missions']} missions cleared. "
            "Super Starter resets story to 0 and overwrites inventory. Pass --force to override."
        )

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
        iid = int.from_bytes(sav_data[addr : addr + 2], "little")
        if iid != 0:
            orig_flags[iid] = sav_data[addr + 3]

    for idx, eid in enumerate(EQUIPMENT_IDS):
        addr = sec1_offset + 0x940 + idx * 4
        sav_data[addr : addr + 2] = eid.to_bytes(2, "little")
        sav_data[addr + 2] = equip_qty
        sav_data[addr + 3] = orig_flags.get(eid, 0)

    for idx, cid in enumerate(CONSUMABLE_IDS):
        addr = sec1_offset + 0xEE4 + idx * 4
        sav_data[addr : addr + 2] = cid.to_bytes(2, "little")
        sav_data[addr + 2] = item_qty
        sav_data[addr + 3] = 0

    print(
        f"  [+] Injected {len(EQUIPMENT_IDS)} weapons/gear ({equip_qty}x) "
        f"and {len(CONSUMABLE_IDS)} consumables ({item_qty}x)."
    )

    # 5. Recalculate CRC32
    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)
    print(f"  [+] Super Starter complete. Checksum: {hex(new_crc)}")
    return sav_data
