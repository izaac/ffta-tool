"""Command Line Interface (CLI) entry point for FFTA Save Tool."""

import argparse
import os
import sys

from .builder import equip_unit_build, inject_unit, rename_unit
from .config import load_config
from .patcher import (
    clear_clan_cards,
    inject_monster_bank,
    patch_clan_units,
    patch_super_starter,
)
from .roster import inspect_save
from .save import atomic_write, auto_detect_save, create_snapshot_backup, fix_crc


def main():
    """Main CLI entry point for ffta-tool."""
    # Pre-parse --config to load defaults before initializing full parser
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", help="Path to custom TOML configuration file")
    pre_args, _ = pre_parser.parse_known_args()

    config = {}
    try:
        config = load_config(pre_args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    cfg_paths = config.get("paths", {})
    cfg_defs = config.get("defaults", {})

    default_slot = cfg_defs.get("slot", 2)
    default_equip = cfg_defs.get("equip_qty", 10)
    default_item = cfg_defs.get("item_qty", 99)
    default_save = cfg_paths.get("save_file")
    default_auto_backup = cfg_defs.get("backup", True)
    custom_backup_dir = cfg_paths.get("backup_dir")

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
  %(prog)s --config custom.toml           # Run with custom TOML configuration
        """,
    )
    parser.add_argument(
        "save_file",
        nargs="?",
        default=default_save,
        help="Path to FFTA save file (.sav). Auto-detected if omitted.",
    )
    parser.add_argument(
        "-i",
        "--inspect",
        action="store_true",
        help="Display full save diagnostic & clan roster",
    )
    parser.add_argument(
        "-p",
        "--patch-units",
        action="store_true",
        help="Master skills & unlock advanced jobs for recruits",
    )
    parser.add_argument("-u", "--unit", type=int, help="Target specific unit index (0..23) for patching")
    parser.add_argument(
        "-s",
        "--super-starter",
        action="store_true",
        help="Apply complete Super Starter patch",
    )
    parser.add_argument(
        "-b",
        "--backup",
        action="store_true",
        help="Create a timestamped snapshot backup without changes",
    )
    parser.add_argument(
        "-c",
        "--clear-cards",
        action="store_true",
        help="Clear all yellow and red cards for clan members",
    )
    parser.add_argument(
        "-m",
        "--inject-monsters",
        action="store_true",
        help="Populate Cyril Monster Bank with all 20 monsters to unlock Morpher abilities",
    )
    parser.add_argument(
        "--monster-level",
        type=int,
        default=None,
        help="Monster level for Cyril Monster Bank (1..99, default: 30)",
    )
    parser.add_argument(
        "--monster-stats",
        type=int,
        default=None,
        help="Base stats for Cyril Monster Bank (50..999, default: level * 10 or 300)",
    )
    parser.add_argument(
        "--monster-affection",
        type=int,
        default=100,
        help="Monster affection for Cyril Monster Bank (0..100, default: 100)",
    )
    parser.add_argument(
        "--fix-crc",
        action="store_true",
        help="Recalculate and write valid CRC checksum",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=default_slot,
        choices=[1, 2],
        help=f"Target save slot (1 or 2, default: {default_slot})",
    )
    parser.add_argument(
        "--equip-qty",
        type=int,
        default=default_equip,
        help=f"Equipment quantity for Super Starter (default: {default_equip})",
    )
    parser.add_argument(
        "--item-qty",
        type=int,
        default=default_item,
        help=f"Consumable quantity for Super Starter (default: {default_item})",
    )
    parser.add_argument(
        "--no-backup",
        dest="auto_backup",
        action="store_false",
        help="Disable automatic pre-patch snapshot backups",
    )
    parser.add_argument(
        "--auto-backup",
        dest="auto_backup",
        action="store_true",
        help="Enable automatic pre-patch snapshot backups",
    )
    parser.set_defaults(auto_backup=default_auto_backup)
    parser.add_argument(
        "--re-equip",
        action="store_true",
        help="Re-equip unit(s) with matching optimal build from builds.toml",
    )
    parser.add_argument(
        "--build",
        help="Specific build key from builds.toml to equip (e.g. gladiator, paladin, assassin)",
    )
    parser.add_argument(
        "--inject",
        help="Inject a god-rolled recruit from builds.toml or job name (e.g. morpher, dragoon, assassin, paladin)",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=None,
        help="Recruit level for injected unit (default: auto-calculated from clan average)",
    )
    parser.add_argument(
        "--name",
        help="Custom recruit name (from FFTA ROM database) for injected unit",
    )
    parser.add_argument(
        "--rename",
        help="Rename an existing unit (specify --unit N, and custom name or 'auto' for random ROM name)",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force patch even if save has cleared missions or story progress",
    )
    parser.add_argument(
        "--config",
        help="Path to custom TOML configuration file",
    )
    parser.add_argument("-o", "--output", help="Output path (default: overwrite input file atomically)")

    args = parser.parse_args()

    # Input validation / safety guards
    if args.monster_level is not None and not (1 <= args.monster_level <= 99):
        parser.error(f"--monster-level must be between 1 and 99 (got {args.monster_level})")

    if args.monster_stats is not None and not (1 <= args.monster_stats <= 999):
        parser.error(f"--monster-stats must be between 1 and 999 (got {args.monster_stats})")

    if args.monster_affection is not None and not (0 <= args.monster_affection <= 100):
        parser.error(f"--monster-affection must be between 0 and 100 (got {args.monster_affection})")

    if args.level is not None and not (1 <= args.level <= 99):
        parser.error(f"--level must be between 1 and 99 (got {args.level})")

    if args.unit is not None and not (0 <= args.unit <= 23):
        parser.error(f"--unit must be between 0 and 23 (got {args.unit})")

    if args.equip_qty is not None and not (1 <= args.equip_qty <= 99):
        parser.error(f"--equip-qty must be between 1 and 99 (got {args.equip_qty})")

    if args.item_qty is not None and not (1 <= args.item_qty <= 99):
        parser.error(f"--item-qty must be between 1 and 99 (got {args.item_qty})")

    # Save file resolution
    target_path = args.save_file
    if target_path:
        target_path = os.path.expanduser(target_path)
    else:
        target_path = auto_detect_save(config)
        if target_path:
            print(f"[*] Auto-detected save: {target_path}")
        else:
            print(
                "Error: No save file specified and none found in common paths.",
                file=sys.stderr,
            )
            sys.exit(1)

    if not os.path.exists(target_path):
        print(f"Error: Save file not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    # Standalone backup
    if args.backup:
        b_path = create_snapshot_backup(target_path, "manual_backup", backup_dir=custom_backup_dir)
        print(f"[+] Created snapshot backup: {b_path}")
        return

    with open(target_path, "rb") as f:
        data = bytearray(f.read())

    if len(data) < 0x10000:
        print(f"Error: Invalid save file size ({len(data)} bytes). Expected at least 65536 bytes for GBA Flash.", file=sys.stderr)
        sys.exit(1)

    target_slot = args.slot - 1

    monster_bank_action = (
        args.inject_monsters
        or args.monster_level is not None
        or args.monster_stats is not None
    )

    # Default action: Inspect
    is_modifying = (
        args.patch_units
        or args.super_starter
        or args.clear_cards
        or monster_bank_action
        or args.fix_crc
        or args.re_equip
        or args.build
        or args.inject
        or args.rename
    )
    if not is_modifying or args.inspect:
        inspect_save(data, show_roster=True)
        if not is_modifying:
            return

    # Automatic snapshot backup before modification
    if args.auto_backup:
        action_name = (
            "super_starter"
            if args.super_starter
            else "inject_unit"
            if args.inject
            else "inject_monsters"
            if monster_bank_action
            else "rename_unit"
            if args.rename
            else "patch_units"
            if args.patch_units
            else "clear_cards"
            if args.clear_cards
            else "re_equip"
            if (args.re_equip or args.build)
            else "crc_fix"
        )
        b_path = create_snapshot_backup(target_path, action_name, backup_dir=custom_backup_dir)
        print(f"[*] Created pre-patch snapshot backup: {b_path}")

    # Modifications
    if args.inject:
        data, _ = inject_unit(
            data,
            build_or_job=args.inject,
            target_slot=target_slot,
            target_unit=args.unit,
            level=args.level,
            name=args.name,
        )

    if args.rename and not args.inject:
        if args.unit is None:
            print("Error: --rename requires --unit <index> (0..23)", file=sys.stderr)
            sys.exit(1)
        data, _ = rename_unit(
            data,
            target_unit=args.unit,
            new_name=args.rename if args.rename.lower() != "auto" else None,
            target_slot=target_slot,
        )

    if args.patch_units and not args.inject:
        data = patch_clan_units(data, target_slot=target_slot, target_unit=args.unit)

    if args.super_starter:
        m_lvl = args.monster_level if args.monster_level is not None else 30
        data = patch_super_starter(
            data,
            target_slot=target_slot,
            equip_qty=args.equip_qty,
            item_qty=args.item_qty,
            force=args.force,
            monster_level=m_lvl,
            monster_stats=args.monster_stats,
        )

    if args.clear_cards and not args.patch_units and not args.super_starter and not args.inject:
        data = clear_clan_cards(data, target_slot=target_slot)

    if monster_bank_action and not args.super_starter:
        m_lvl = args.monster_level if args.monster_level is not None else 30
        data = inject_monster_bank(
            data,
            target_slot=target_slot,
            level=m_lvl,
            affection=args.monster_affection,
            stats=args.monster_stats,
        )

    if (args.re_equip or args.build) and not args.patch_units and not args.super_starter and not args.inject:
        data = equip_unit_build(
            data,
            target_slot=target_slot,
            target_unit=args.unit,
            build_key=args.build,
        )

    if (
        args.fix_crc
        and not args.patch_units
        and not args.super_starter
        and not args.clear_cards
        and not args.re_equip
        and not args.inject
        and not args.rename
    ):
        data = fix_crc(data, target_slot=target_slot)

    # Atomic write
    out_path = args.output if args.output else target_path
    atomic_write(out_path, data)
    print(f"\n[+] Successfully saved to: {out_path}")
    print("\n[!] NOTE: Ensure game is closed / restarted on NextUI handheld to reload save!")


if __name__ == "__main__":
    main()
