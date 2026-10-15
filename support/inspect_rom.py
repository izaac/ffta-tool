#!/usr/bin/env python3
"""FFTA ROM & Data Inspector Tool.

High-value, token-saving CLI utility to quickly inspect:
- Job base stats and growths table (ROM offset 0x521A80)
- Item database (weapons, armor, accessories, IDs, stats)
- Recruit names and ID mappings by race
- Race ability tables and secondary skill configurations
"""

import argparse
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mappings import (
    ALTERNATE_SECONDARY_A_SETS,
    ALTERNATE_SECONDARY_JOBS,
    DEFAULT_SECONDARY_A_SETS,
    DEFAULT_SECONDARY_JOBS,
    JOB_NAMES,
    JOB_STAT_TABLE,
    KNOWN_ITEMS,
    RACE_ABILITY_BASE,
    RACE_ABILITY_SPECS,
    RACE_NAMES,
    RECRUIT_NAMES,
)

DEFAULT_ROM_PATH = "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].gba"


def inspect_jobs(query: str | None = None):
    """Prints base stats and growth rates for jobs."""
    print(f"\n{'=' * 95}")
    header = (
        f"{'ID':<4} {'Job Name':<20} {'Race':<10} {'HP':<4} {'MP':<4} {'Spd':<4} "
        f"{'Atk':<4} {'Def':<4} {'Pow':<4} {'Res':<4} | {'Growths (HP/Spd/Atk/Def/Pow/Res/MP)'}"
    )
    print(header)
    print(f"{'=' * 95}")

    for j_id in sorted(JOB_NAMES.keys()):
        j_name, race = JOB_NAMES[j_id]
        if query:
            clean = query.lower()
            matches_id = clean in (str(j_id), hex(j_id))
            if clean not in j_name.lower() and clean not in race.lower() and not matches_id:
                continue

        stats = JOB_STAT_TABLE.get(j_id)
        if stats:
            hp, mp, spd, watk, wdef, mpow, mres, hpg, spdg, atkg, defg, powg, resg, mpg = stats
            grow_str = f"{hpg:4.1f}/{spdg:3.1f}/{atkg:4.1f}/{defg:4.1f}/{powg:4.1f}/{resg:4.1f}/{mpg:3.1f}"
            print(
                f"{hex(j_id):<4} {j_name:<20} {race:<10} {int(hp):<4} {int(mp):<4} {int(spd):<4} "
                f"{int(watk):<4} {int(wdef):<4} {int(mpow):<4} {int(mres):<4} | {grow_str}"
            )
        else:
            print(f"{hex(j_id):<4} {j_name:<20} {race:<10} [No Stat Data]")


def inspect_items(query: str | None = None):
    """Searches and prints items from the KNOWN_ITEMS dictionary."""
    print(f"\n{'=' * 60}")
    print(f"{'Hex ID':<8} {'Dec ID':<8} {'Item Name'}")
    print(f"{'=' * 60}")

    matches = 0
    for i_id, name in sorted(KNOWN_ITEMS.items()):
        if query:
            clean = query.lower()
            if clean not in name.lower() and clean != hex(i_id).lower() and clean != str(i_id):
                continue
        matches += 1
        print(f"{hex(i_id):<8} {i_id:<8} {name}")

    print(f"\nTotal matches: {matches}")


def inspect_names(query: str | None = None, race_name: str | None = None):
    """Searches recruit names or lists names for a specific race."""
    print(f"\n{'=' * 60}")
    print(f"{'ID':<6} {'Name':<20} {'Category / Gender'}")
    print(f"{'=' * 60}")

    matches = 0
    for idx, name in enumerate(RECRUIT_NAMES):
        if idx < 320:
            cat = "Hume / Moogle (Male Pool)"
        elif idx < 500:
            cat = "Viera (Female Pool)"
        else:
            cat = "Bangaa / Nu Mou (Exotic Pool)"

        if race_name:
            rn = race_name.lower()
            if rn == "viera" and not (320 <= idx < 500):
                continue
            if rn in ("bangaa", "nu mou", "numou") and idx < 500:
                continue
            if rn in ("hume", "moogle") and idx >= 320:
                continue

        if query:
            clean = query.lower()
            if clean not in name.lower() and clean != str(idx) and clean != hex(idx):
                continue

        matches += 1
        if matches <= 100:
            print(f"{idx:<6} {name:<20} {cat}")

    if matches > 100:
        print(f"... [{matches - 100} more names omitted. Use a more specific query]")
    print(f"\nTotal matches: {matches}")


def inspect_races():
    """Prints race specifications and default ability configurations."""
    print(f"\n{'=' * 78}")
    print("CANONICAL RACE & ABILITY CONFIGURATIONS")
    print(f"{'=' * 78}")
    for r_id, r_name in sorted(RACE_NAMES.items()):
        base = RACE_ABILITY_BASE.get(r_id, "?")
        specs = RACE_ABILITY_SPECS.get(r_id, (0, 0, False))
        def_sec_j = DEFAULT_SECONDARY_JOBS.get(r_id, "?")
        def_sec_j_name = JOB_NAMES.get(def_sec_j, ("?", ""))[0]
        alt_sec_j = ALTERNATE_SECONDARY_JOBS.get(r_id, "?")
        alt_sec_j_name = JOB_NAMES.get(alt_sec_j, ("?", ""))[0]
        def_set = DEFAULT_SECONDARY_A_SETS.get(r_id, "?")
        alt_set = ALTERNATE_SECONDARY_A_SETS.get(r_id, "?")

        print(f"\nRace {r_id}: {r_name}")
        print(f"  Ability Table Base: {base} (0x{base:02X})")
        print(f"  Abilities Count: {specs[0]} (Blue Magic: {specs[1]}, Morpher: {specs[2]})")
        print(f"  Default Secondary: {def_sec_j_name} (Job {def_sec_j}, Set {def_set})")
        print(f"  Alternate Secondary (Anti-Dupe): {alt_sec_j_name} (Job {alt_sec_j}, Set {alt_set})")


def main():
    parser = argparse.ArgumentParser(description="FFTA ROM Table and Constants Inspector")
    parser.add_argument("--job", nargs="?", const="all", help="Inspect job base stats and growths (name, id, or 'all')")
    parser.add_argument("--item", nargs="?", const="all", help="Search item database by name or ID")
    parser.add_argument("--name", nargs="?", const="all", help="Search recruit name database by name or ID")
    parser.add_argument("--race", help="Filter names or show race details (Hume, Bangaa, Nu Mou, Viera, Moogle)")
    parser.add_argument("--races", action="store_true", help="Display all race configurations and default sets")
    args = parser.parse_args()

    if not any([args.job, args.item, args.name, args.race, args.races]):
        parser.print_help()
        sys.exit(0)

    if args.races:
        inspect_races()
    if args.job:
        inspect_jobs(None if args.job == "all" else args.job)
    if args.item:
        inspect_items(None if args.item == "all" else args.item)
    if args.name or args.race:
        inspect_names(None if args.name == "all" else args.name, race_name=args.race)


if __name__ == "__main__":
    main()
