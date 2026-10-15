#!/usr/bin/env python3
"""FFTA Analogue Pocket SD Card Synchronization Tool.

Synchronizes canonical ROMs (.gba) and saves (.sav) between local FFTA_Assets
and the Analogue Pocket SD card filesystem, then triggers an OS sync.
"""

import argparse
import hashlib
import os
import shutil
import sys

DEFAULT_ASSET_DIR = os.environ.get(
    "FFTA_ASSET_DIR",
    os.path.expanduser("~/Documents/FFTA_Assets"),
)


def find_pocket_base() -> str:
    """Dynamically locates the Analogue Pocket SD card mount point."""
    if "POCKET_DIR" in os.environ and os.path.exists(os.environ["POCKET_DIR"]):
        return os.environ["POCKET_DIR"]

    for mount_root in ["/run/media", "/media", "/mnt", "/Volumes"]:
        if os.path.exists(mount_root):
            try:
                for entry in os.listdir(mount_root):
                    # Direct mount (e.g. /Volumes/POCKET)
                    if entry.upper() == "POCKET":
                        p = os.path.join(mount_root, entry)
                        if os.path.isdir(p):
                            return p
                    # Sub-user mount (e.g. /run/media/<user>/POCKET)
                    sub = os.path.join(mount_root, entry)
                    if os.path.isdir(sub):
                        p = os.path.join(sub, "POCKET")
                        if os.path.exists(p) and os.path.isdir(p):
                            return p
            except OSError:
                continue

    return os.environ.get("POCKET_DIR", "/Volumes/POCKET")


DEFAULT_POCKET_BASE = find_pocket_base()


def get_file_md5(path: str) -> str:
    """Calculates MD5 digest of a file in chunks."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sync_file(src_path: str, dst_path: str, dry_run: bool = False) -> bool:
    """Copies src to dst if dst does not exist or MD5 differs."""
    if not os.path.exists(src_path):
        print(f"[-] Source file does not exist: {src_path}")
        return False

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    if os.path.exists(dst_path):
        src_md5 = get_file_md5(src_path)
        dst_md5 = get_file_md5(dst_path)
        if src_md5 == dst_md5:
            print(f"  [=] Up-to-date: {os.path.basename(dst_path)}")
            return False

    if dry_run:
        print(f"  [*] [DRY-RUN] Would copy {os.path.basename(src_path)} -> {dst_path}")
        return True

    print(f"  [+] Copying {os.path.basename(src_path)} -> {dst_path}")
    shutil.copy2(src_path, dst_path)
    return True


def sync_pocket(asset_dir: str = DEFAULT_ASSET_DIR, pocket_base: str = DEFAULT_POCKET_BASE, dry_run: bool = False):
    """Syncs all FFTA ROMs and saves from assets to Pocket."""
    if not os.path.exists(pocket_base):
        print(f"[-] Pocket SD card not detected at {pocket_base}")
        sys.exit(1)

    if not os.path.exists(asset_dir):
        print(f"[-] Asset directory not found at {asset_dir}")
        sys.exit(1)

    print(f"{'=' * 78}")
    print("FFTA ANALOGUE POCKET SYNC")
    print(f"Source: {asset_dir}")
    print(f"Target: {pocket_base}")
    print(f"{'=' * 78}\n")

    files = sorted(os.listdir(asset_dir))
    gbas = [f for f in files if f.startswith("Final Fantasy Tactics Advance") and f.endswith(".gba")]
    savs = [f for f in files if f.startswith("Final Fantasy Tactics Advance") and f.endswith(".sav")]

    rom_target = os.path.join(pocket_base, "Assets/gba/common")
    save_target1 = os.path.join(pocket_base, "Saves/gba")
    save_target2 = os.path.join(pocket_base, "Saves/gba/common")

    copied_count = 0

    print(">>> Syncing GBA ROMs...")
    for rom in gbas:
        src = os.path.join(asset_dir, rom)
        dst = os.path.join(rom_target, rom)
        if sync_file(src, dst, dry_run=dry_run):
            copied_count += 1

    print("\n>>> Syncing Save Files (.sav)...")
    for sav in savs:
        src = os.path.join(asset_dir, sav)
        dst1 = os.path.join(save_target1, sav)
        dst2 = os.path.join(save_target2, sav)
        if sync_file(src, dst1, dry_run=dry_run):
            copied_count += 1
        if sync_file(src, dst2, dry_run=dry_run):
            copied_count += 1

    if not dry_run and copied_count > 0:
        print("\n[*] Flushing OS filesystem buffers (sync)...")
        os.sync()
        print("[+] Filesystem buffers flushed successfully.")

    print(f"\n{'=' * 78}")
    print(f"Sync complete! {copied_count} file(s) updated.")
    print(f"{'=' * 78}")


def main():
    parser = argparse.ArgumentParser(description="Sync FFTA ROMs and saves to Analogue Pocket SD card")
    parser.add_argument("--assets", default=DEFAULT_ASSET_DIR, help="Path to local FFTA_Assets directory")
    parser.add_argument("--pocket", default=DEFAULT_POCKET_BASE, help="Mount point for Analogue Pocket SD card")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Perform a trial run without writing files")
    args = parser.parse_args()

    sync_pocket(asset_dir=args.assets, pocket_base=args.pocket, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
