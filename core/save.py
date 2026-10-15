"""Save file operations, wear-leveling sector resolution, and CRC32 verification."""

import contextlib
import glob
import os
import shutil
import struct
import zlib
from datetime import datetime
from pathlib import Path

from .config import get_default_backup_dir

SECTOR_SIZE = 0x1000
MAGIC = b"FFTEX000"


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


def auto_detect_save(config=None):
    """Attempts to find the most relevant FFTA save file automatically."""
    candidates = []

    cfg_paths = config.get("paths", {}) if config else {}
    custom_search_paths = cfg_paths.get("search_paths")

    if custom_search_paths:
        for pattern in custom_search_paths:
            expanded = os.path.expanduser(pattern)
            candidates.extend(glob.glob(expanded))
    else:
        # Check removable media mounts dynamically across system mount points
        for mount_root in ["/run/media", "/media", "/mnt", "/Volumes"]:
            candidates.extend(glob.glob(f"{mount_root}/*/*/Saves/GBA/*Final Fantasy Tactics Advance*.sav"))
            candidates.extend(glob.glob(f"{mount_root}/*/*/Saves/gba/*Final Fantasy Tactics Advance*.sav"))
            candidates.extend(glob.glob(f"{mount_root}/*/Saves/GBA/*Final Fantasy Tactics Advance*.sav"))
            candidates.extend(glob.glob(f"{mount_root}/*/Saves/gba/*Final Fantasy Tactics Advance*.sav"))

        if os.name == "nt":
            import string
            for letter in string.ascii_uppercase[2:]:
                candidates.extend(glob.glob(f"{letter}:\\Saves\\gba\\*Final Fantasy Tactics Advance*.sav"))
                candidates.extend(glob.glob(f"{letter}:\\Saves\\GBA\\*Final Fantasy Tactics Advance*.sav"))

        try:
            home_path = Path.home()
            doc_dir = home_path / "Documents"
            backup_dir = doc_dir / "FFTA_Backups"
            asset_dir = doc_dir / "FFTA_Assets"
            candidates.extend(
                [
                    str(asset_dir / "Final Fantasy Tactics Advance (U) [!].sav"),
                    str(doc_dir / "FFTA_Save_Slot2_Mastered_Recruits_Juggler.sav"),
                    str(backup_dir / "FFTA_Save_Slot2_Mastered_Recruits_Juggler.sav"),
                    str(backup_dir / "Final_Fantasy_Tactics_Advance_Current_Patched.sav"),
                ]
            )
            if asset_dir.is_dir():
                candidates.extend(glob.glob(str(asset_dir / "*.sav")))
            if backup_dir.is_dir():
                candidates.extend(glob.glob(str(backup_dir / "*.sav")))
        except Exception:
            pass

        # Fallback to current directory .sav files
        candidates.extend(glob.glob("*.sav"))

    for p in candidates:
        if os.path.isfile(p) and os.path.getsize(p) >= 0x10000:
            return p

    return None


def create_snapshot_backup(filepath, action_name="update", backup_dir=None):
    """Creates a timestamped snapshot in the backups directory before writing."""
    b_dir = get_default_backup_dir(backup_dir)
    b_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    clean_base = base_name.replace("Final Fantasy Tactics Advance (USA, Australia).zip", "FFTA")
    backup_filename = f"{clean_base}_{action_name}_{ts}.sav"
    backup_path = str(b_dir / backup_filename)
    shutil.copy2(filepath, backup_path)
    return backup_path


def atomic_write(filepath, data):
    """Safely writes data to a temporary file then replaces target atomically."""
    dir_name = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(dir_name, exist_ok=True)
    tmp_path = filepath + f".tmp_{os.getpid()}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
        if hasattr(os, "sync"):
            with contextlib.suppress(AttributeError, OSError):
                os.sync()
    finally:
        if os.path.exists(tmp_path):
            with contextlib.suppress(OSError):
                os.remove(tmp_path)


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
