"""Unit build resolution, recruit injection, equipment equipping, and renaming."""

import struct

try:
    from mappings import (
        ALTERNATE_SECONDARY_A_SETS,
        ALTERNATE_SECONDARY_JOBS,
        DEFAULT_COMBO_IDS,
        DEFAULT_REACTION_IDS,
        DEFAULT_SECONDARY_A_SETS,
        DEFAULT_SECONDARY_JOBS,
        DEFAULT_SUPPORT_IDS,
        JOB_NAMES,
        JOB_PRIMARY_A_SETS,
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
except ImportError:
    from ..mappings import (
        ALTERNATE_SECONDARY_A_SETS,
        ALTERNATE_SECONDARY_JOBS,
        DEFAULT_COMBO_IDS,
        DEFAULT_REACTION_IDS,
        DEFAULT_SECONDARY_A_SETS,
        DEFAULT_SECONDARY_JOBS,
        DEFAULT_SUPPORT_IDS,
        JOB_NAMES,
        JOB_PRIMARY_A_SETS,
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

from .config import load_builds
from .save import SECTOR_SIZE, compute_crc, get_slots


def equip_unit_build(
    sav_data: bytearray,
    target_slot: int = 1,
    target_unit: int | None = None,
    build_key: str | None = None,
    builds_path: str | None = None,
    bump_counter: bool = True,
) -> bytearray:
    """Equips a unit with an optimal build from the database."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found!")

    if target_unit is not None and not (0 <= target_unit < 24):
        raise ValueError(f"target_unit must be between 0 and 23 (got {target_unit}).")

    builds = load_builds(builds_path)
    if not builds:
        print("  [!] Notice: No builds database found. Skipping build equip.")
        return sav_data

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]
    hdr_offset = hdr_sec * SECTOR_SIZE

    equipped_count = 0
    units_to_process = [target_unit] if target_unit is not None else list(range(24))

    for u in units_to_process:
        u_addr = hdr_offset + 0x80 + u * 0x108
        if u_addr + 0x108 > len(sav_data):
            break
        level = sav_data[u_addr + 0x09]
        if level == 0:
            continue

        race_id = sav_data[u_addr + 0x06]
        job_id = sav_data[u_addr + 0x07]
        race_name = RACE_NAMES.get(race_id, "")
        job_name = JOB_NAMES.get(job_id, ("", ""))[0]

        selected_build = None
        if build_key and build_key in builds:
            selected_build = builds[build_key]
        else:
            for b_info in builds.values():
                if (
                    b_info.get("job", "").lower() == job_name.lower()
                    and b_info.get("race", "").lower() == race_name.lower()
                ):
                    selected_build = b_info
                    break

        if selected_build and "gear" in selected_build:
            gear = selected_build["gear"]
            if len(gear) >= 5:
                gear_bytes = struct.pack("<5H", *gear[:5])
                sav_data[u_addr + 0x2A : u_addr + 0x34] = gear_bytes
                gear_str = ", ".join(selected_build.get("gear_names", [hex(g) for g in gear[:5]]))
                b_name = selected_build.get("name", "Build")
                print(f"  [+] Unit {u} ({race_name} {job_name}): Equipped {b_name} [{gear_str}]")
                equipped_count += 1

    if bump_counter and equipped_count > 0:
        new_counter = info["counter"] + 1
        sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)
        new_crc = compute_crc(sav_data, secs)
        sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)
        print(f"  [+] Sequence counter incremented to: {new_counter}")
        print(f"  [+] Checksum updated: {hex(new_crc)}")

    return sav_data


def resolve_job_and_race(query: str, builds_path: str | None = None) -> tuple[int, int, list[int], str]:
    """Resolves a build key or job string into (job_id, race_id, gear_list, display_name)."""
    clean = query.strip().lower()
    norm_key = clean.replace("-", "_").replace(" ", "_")

    builds = load_builds(builds_path)
    selected_build = None

    # 1. Exact match in builds.toml by key
    if norm_key in builds:
        selected_build = builds[norm_key]
    else:
        # 2. Match in builds.toml by name or (race + job) or job
        for b_key, b_val in builds.items():
            b_name = b_val.get("name", "").lower()
            b_job = b_val.get("job", "").lower()
            b_race = b_val.get("race", "").lower()
            combined = f"{b_race} {b_job}".lower()
            if clean in (b_key, b_name, b_job, combined) or norm_key in (
                b_key,
                b_job.replace(" ", "_"),
                combined.replace(" ", "_"),
            ):
                selected_build = b_val
                break

    if selected_build:
        b_race = selected_build.get("race", "")
        b_job = selected_build.get("job", "")
        race_id = next((r_id for r_id, r_name in RACE_NAMES.items() if r_name.lower() == b_race.lower()), None)
        if race_id is None:
            raise ValueError(f"Unknown race in build: {b_race}")
        job_id = selected_build.get("job_id")
        if job_id is None:
            job_id = next(
                (
                    j_id
                    for j_id, (j_name, j_race) in JOB_NAMES.items()
                    if j_name.lower() == b_job.lower() and j_race.lower() == b_race.lower()
                ),
                None,
            )
        if job_id is None:
            raise ValueError(f"Unknown job in build: {b_job} ({b_race})")
        gear = selected_build.get("gear", [0, 0, 0, 0, 0])
        display_name = selected_build.get("name", f"{b_race} {b_job}")
        return job_id, race_id, gear, display_name

    # 3. Match against JOB_NAMES directly
    for j_id, (j_name, j_race) in JOB_NAMES.items():
        combined = f"{j_race} {j_name}".lower()
        if clean == combined or norm_key == combined.replace(" ", "_"):
            race_id = next(r_id for r_id, r_name in RACE_NAMES.items() if r_name.lower() == j_race.lower())
            return j_id, race_id, [0, 0, 0, 0, 0], f"{j_race} {j_name}"

    for j_id, (j_name, j_race) in JOB_NAMES.items():
        if clean == j_name.lower() or norm_key == j_name.lower().replace(" ", "_"):
            race_id = next(r_id for r_id, r_name in RACE_NAMES.items() if r_name.lower() == j_race.lower())
            return j_id, race_id, [0, 0, 0, 0, 0], f"{j_race} {j_name}"

    raise ValueError(f"Unknown build or job type: '{query}'. Check builds.toml or specify a canonical job name.")


def inject_unit(
    sav_data: bytearray,
    build_or_job: str,
    target_slot: int = 1,
    target_unit: int | None = None,
    level: int | None = None,
    name: str | None = None,
    builds_path: str | None = None,
) -> tuple[bytearray, dict]:
    """Injects a god-rolled, max-ability recruit into the clan."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in save file!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]
    hdr_offset = hdr_sec * SECTOR_SIZE

    # Resolve target unit slot (auto-detect first empty slot if not specified)
    if target_unit is None:
        for u in range(24):
            u_addr = hdr_offset + 0x80 + u * 0x108
            if u_addr + 0x108 <= len(sav_data) and sav_data[u_addr + 0x09] == 0:
                target_unit = u
                break
        if target_unit is None:
            raise ValueError("Clan is full! All 24 unit slots are occupied.")
    elif not (0 <= target_unit < 24):
        raise ValueError(f"Invalid unit index {target_unit}. Must be 0..23.")

    if level is not None and not (1 <= level <= 99):
        raise ValueError(f"Recruit level must be between 1 and 99 (got {level}).")

    # Collect existing names across clan to avoid duplicate recruit names
    existing_name_ids = set()
    for u in range(24):
        u_addr = hdr_offset + 0x80 + u * 0x108
        if u_addr + 0x108 <= len(sav_data) and sav_data[u_addr + 0x09] > 0 and u != target_unit:
            nid = struct.unpack("<H", sav_data[u_addr : u_addr + 2])[0]
            existing_name_ids.add(nid)

    # Resolve job, race, gear, and build title
    job_id, race_id, gear, build_title = resolve_job_and_race(build_or_job, builds_path=builds_path)
    race_name = RACE_NAMES[race_id]
    job_title = JOB_NAMES[job_id][0]

    # Resolve unit name
    if name is not None:
        clean_name = str(name).strip()
        if clean_name.isdigit():
            name_id = int(clean_name)
            unit_name = get_unit_name(name_id)
        else:
            resolved_id = get_name_id_by_str(clean_name)
            if resolved_id is None:
                raise ValueError(f"Name '{clean_name}' not found in FFTA ROM database.")
            name_id = resolved_id
            unit_name = RECRUIT_NAMES[name_id]
    else:
        name_id, unit_name = generate_random_name(race_id, excluded_ids=existing_name_ids)

    # Resolve unit level via canonical clan average formula if not specified
    if level is None:
        active_levels = []
        for u in range(24):
            u_addr = hdr_offset + 0x80 + u * 0x108
            if u_addr + 0x108 <= len(sav_data) and u != target_unit:
                u_lvl = sav_data[u_addr + 0x09]
                if u_lvl > 0:
                    active_levels.append(u_lvl)
        base_level = sum(active_levels) // len(active_levels) if active_levels else 1
        is_advanced = job_title not in (
            "Soldier",
            "Archer",
            "Thief",
            "White Mage",
            "Black Mage",
            "Warrior",
            "White Monk",
            "Animist",
            "Fencer",
            "Beastmaster",
        )
        level = base_level + (1 if is_advanced else 0)
    level = max(1, min(50, level))

    # Compute 115% top-rolled god stats
    stats = compute_god_stats(job_id, level=level)

    # Build pristine 0x108 unit block
    ub = bytearray(0x108)

    # 0x00..0x04: Name ID
    ub[0x00:0x02] = struct.pack("<H", name_id)
    # 0x04: Special recruit flag (1 = standard clan member)
    ub[0x04] = 1
    # 0x05: Sprite / Job index
    ub[0x05] = job_id
    # 0x06: Race ID
    ub[0x06] = race_id
    # 0x07: Primary Job ID
    ub[0x07] = job_id
    # 0x08: Secondary Job ID & 0x36: Secondary A-ability set (fallback to alternate to prevent duplicate skills)
    def_sec = DEFAULT_SECONDARY_JOBS.get(race_id, job_id)
    if def_sec == job_id:
        sec_job_id = ALTERNATE_SECONDARY_JOBS.get(race_id, job_id)
        sec_a_set = ALTERNATE_SECONDARY_A_SETS.get(race_id, 4)
    else:
        sec_job_id = def_sec
        sec_a_set = DEFAULT_SECONDARY_A_SETS.get(race_id, 4)
    ub[0x08] = sec_job_id
    # 0x09: Level
    ub[0x09] = level
    # 0x0A:0x0C: EXP = 0
    ub[0x0A:0x0C] = b"\x00\x00"
    # 0x0C:0x16: Base job masteries
    ub[0x0C:0x16] = bytes([1] * 10)

    # 0x18:0x28: Cur HP, Max HP, Cur MP, Max MP, WAtk, WDef, MPow, MRes
    ub[0x18:0x28] = struct.pack(
        "<8H",
        stats["hp"],
        stats["hp"],
        stats["mp"],
        stats["mp"],
        stats["watk"],
        stats["wdef"],
        stats["mpow"],
        stats["mres"],
    )

    # 0x2A:0x34: Equipment
    full_gear = list(gear[:5]) + [0] * (5 - len(gear[:5]))
    ub[0x2A:0x34] = struct.pack("<5H", *full_gear)

    # 0x34: Race ability table base
    ub[0x34] = RACE_ABILITY_BASE.get(race_id, 142)
    # 0x35: Primary A-ability set
    ub[0x35] = JOB_PRIMARY_A_SETS.get(job_id, 2)
    # 0x36: Secondary A-ability set
    ub[0x36] = sec_a_set
    # 0x3A: Reaction ability
    ub[0x3A] = DEFAULT_REACTION_IDS.get(race_id, 0)
    # 0x3B: Support ability
    ub[0x3B] = DEFAULT_SUPPORT_IDS.get(race_id, 0)
    # 0x3C: Combo ability
    ub[0x3C] = DEFAULT_COMBO_IDS.get(race_id, 0)

    # Master all abilities
    count, blue_magic, morpher = RACE_ABILITY_SPECS.get(race_id, (80, 0, False))
    for i in range(count):
        ub[0x41 + i] = 0xE4
    if blue_magic:
        for i in range(blue_magic):
            ub[0x9C + i] = 0xE4
    if morpher:
        for i in range(12):
            ub[0x93 + i] = 0xE4

    # 0xD2:0xD4: Base Speed
    ub[0xD2:0xD4] = struct.pack("<H", stats["speed"])
    # 0xD6: Growth fractional counter
    ub[0xD6] = 5

    # 0xF1:0x106: Job unlock bitmask counters
    if race_id in RACE_JOB_COUNTERS:
        ub[0xF1:0x106] = RACE_JOB_COUNTERS[race_id]

    # 0x101: Jail battle counter
    ub[0x101] = 0x00
    # 0x102: Red cards
    ub[0x102] = 0x00
    # 0x103: Yellow cards
    ub[0x103] = 0x00
    # 0x104: Unit state (0xFF = Free / Active)
    ub[0x104] = 0xFF

    # Inject into save buffer
    target_addr = hdr_offset + 0x80 + target_unit * 0x108
    sav_data[target_addr : target_addr + 0x108] = ub

    # Increment sequence counter
    new_counter = info["counter"] + 1
    sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)

    # Recompute CRC32
    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)

    inject_summary = {
        "unit_idx": target_unit,
        "name": unit_name,
        "name_id": name_id,
        "race": race_name,
        "job": job_title,
        "build": build_title,
        "level": level,
        "stats": stats,
        "counter": new_counter,
        "crc": new_crc,
    }

    print(f'  [+] Injected Unit {target_unit}: "{unit_name}" ({race_name} {job_title}, Lv {level})')
    print(f"      Build: {build_title}")
    print(
        f"      Stats (115% God Roll): HP {stats['hp']}, MP {stats['mp']}, Spd {stats['speed']}, "
        f"Atk {stats['watk']}, Def {stats['wdef']}, Pow {stats['mpow']}, Res {stats['mres']}"
    )
    print(f"      Abilities: Mastered all {count} skills + advanced jobs unlocked.")
    print(f"      Sequence counter incremented to: {new_counter}")
    print(f"      Checksum updated: {hex(new_crc)}")

    return sav_data, inject_summary


def rename_unit(
    sav_data: bytearray,
    target_unit: int,
    new_name: str | None = None,
    target_slot: int = 1,
) -> tuple[bytearray, str]:
    """Renames an existing unit using a specified name or generating a random ROM name."""
    slots = get_slots(sav_data)
    if target_slot not in slots:
        raise ValueError(f"Slot {target_slot + 1} not found in save file!")

    info = slots[target_slot]
    secs = info["sectors"]
    hdr_sec = secs[0]
    hdr_offset = hdr_sec * SECTOR_SIZE

    if not (0 <= target_unit < 24):
        raise ValueError(f"Invalid unit index {target_unit}.")

    u_addr = hdr_offset + 0x80 + target_unit * 0x108
    if sav_data[u_addr + 0x09] == 0:
        raise ValueError(f"Unit {target_unit} is empty (Level 0).")

    race_id = sav_data[u_addr + 0x06]

    # Collect existing names across clan
    existing_name_ids = set()
    for u in range(24):
        ua = hdr_offset + 0x80 + u * 0x108
        if ua + 0x108 <= len(sav_data) and sav_data[ua + 0x09] > 0 and u != target_unit:
            nid = struct.unpack("<H", sav_data[ua : ua + 2])[0]
            existing_name_ids.add(nid)

    if new_name is not None:
        clean = str(new_name).strip()
        if clean.isdigit():
            name_id = int(clean)
            final_name = get_unit_name(name_id)
        else:
            resolved_id = get_name_id_by_str(clean)
            if resolved_id is None:
                raise ValueError(f"Name '{clean}' not found in FFTA ROM database.")
            name_id = resolved_id
            final_name = RECRUIT_NAMES[name_id]
    else:
        name_id, final_name = generate_random_name(race_id, excluded_ids=existing_name_ids)

    sav_data[u_addr : u_addr + 2] = struct.pack("<H", name_id)

    new_counter = info["counter"] + 1
    sav_data[hdr_offset + 8 : hdr_offset + 12] = struct.pack("<I", new_counter)

    new_crc = compute_crc(sav_data, secs)
    sav_data[hdr_offset + 0x0C : hdr_offset + 0x10] = struct.pack("<I", new_crc)

    print(f'  [+] Renamed Unit {target_unit} to: "{final_name}" (Name ID: {name_id})')
    print(f"  [+] Sequence counter incremented to: {new_counter}")
    print(f"  [+] Checksum updated: {hex(new_crc)}")
    return sav_data, final_name
