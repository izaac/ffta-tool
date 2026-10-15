"""Unit tests for Monster Bank injection and stat packing in FFTA save files."""

import os
import struct
import tempfile
import unittest

from core.patcher import (
    MONSTER_SPECIES,
    inject_monster_bank,
    pack_monster_stats,
    unpack_monster_stats,
)
from core.roster import inspect_save
from core.save import SECTOR_SIZE, compute_crc, get_slots
from support.validate_saves import validate_save_file


class TestMonsterBank(unittest.TestCase):
    """Verifies Monster Bank data structures, bit packing, and injection routines."""

    def test_monster_species_count(self):
        """Monster species list must have exactly 20 entries matching FFTA pens."""
        self.assertEqual(len(MONSTER_SPECIES), 20)
        self.assertEqual(MONSTER_SPECIES[0], "Goblin")
        self.assertEqual(MONSTER_SPECIES[1], "Red Cap")
        self.assertEqual(MONSTER_SPECIES[19], "Ahriman")

    def test_pack_unpack_monster_stats(self):
        """Packs six 10-bit stats and verifies bit-for-bit lossless unpacking."""
        # Test 999 god stats
        packed_999 = pack_monster_stats(999, 999, 999, 999, 999, 999)
        self.assertEqual(len(packed_999), 8)
        unpacked_999 = unpack_monster_stats(packed_999)
        self.assertEqual(unpacked_999, (999, 999, 999, 999, 999, 999))

        # Test distinct stats
        packed_custom = pack_monster_stats(hp=500, mp=120, watk=350, wdef=280, mpow=410, mres=390)
        unpacked_custom = unpack_monster_stats(packed_custom)
        self.assertEqual(unpacked_custom, (500, 120, 350, 280, 410, 390))

        # Test boundary values
        packed_min = pack_monster_stats(0, 0, 0, 0, 0, 0)
        self.assertEqual(unpack_monster_stats(packed_min), (0, 0, 0, 0, 0, 0))

        packed_max = pack_monster_stats(1023, 1023, 1023, 1023, 1023, 1023)
        self.assertEqual(unpack_monster_stats(packed_max), (1023, 1023, 1023, 1023, 1023, 1023))

    def _create_mock_save(self) -> bytearray:
        """Constructs a minimal valid 64K FFTA save buffer with 2 slots."""
        sav = bytearray(0x10000)
        # Slot 1: sectors 0, 1, 2, 3
        hdr0 = bytearray(SECTOR_SIZE)
        hdr0[0:8] = b"FFTEX000"
        hdr0[8:12] = struct.pack("<I", 10)
        hdr0[0x10] = 0  # Slot 1
        hdr0[0x12:0x16] = bytes([0, 1, 2, 3])
        hdr0[0x76:0x78] = struct.pack("<H", 5)
        sav[0:SECTOR_SIZE] = hdr0
        crc0 = compute_crc(sav, [0, 1, 2, 3])
        sav[0x0C:0x10] = struct.pack("<I", crc0)

        # Slot 2: sectors 4, 5, 6, 7
        hdr1 = bytearray(SECTOR_SIZE)
        hdr1[0:8] = b"FFTEX000"
        hdr1[8:12] = struct.pack("<I", 50)
        hdr1[0x10] = 1  # Slot 2
        hdr1[0x12:0x16] = bytes([4, 5, 6, 7])
        hdr1[0x76:0x78] = struct.pack("<H", 20)
        sav[4 * SECTOR_SIZE : 5 * SECTOR_SIZE] = hdr1
        crc1 = compute_crc(sav, [4, 5, 6, 7])
        sav[4 * SECTOR_SIZE + 0x0C : 4 * SECTOR_SIZE + 0x10] = struct.pack("<I", crc1)

        return sav

    def test_inject_monster_bank_success(self):
        """Injects Monster Bank and verifies pen data, sequence bump, and CRC."""
        sav = self._create_mock_save()
        initial_slots = get_slots(sav)
        initial_counter = initial_slots[1]["counter"]

        patched = inject_monster_bank(sav, target_slot=1, level=99, affection=100, stats=999)
        updated_slots = get_slots(patched)

        # 1. Slot must remain valid with updated counter
        self.assertTrue(updated_slots[1]["valid"])
        self.assertEqual(updated_slots[1]["counter"], initial_counter + 1)

        # 2. Verify all 20 pens in Sector 2 (sector 6 for slot 2)
        sec2_off = 6 * SECTOR_SIZE
        bank_addr = sec2_off + 0x0E78
        for i in range(20):
            slot_addr = bank_addr + i * 16
            name_id = int.from_bytes(patched[slot_addr : slot_addr + 2], "little")
            status_flags = patched[slot_addr + 2 : slot_addr + 4]
            active_flag = patched[slot_addr + 4]
            level = patched[slot_addr + 5]
            affection = patched[slot_addr + 7]
            stat_bytes = patched[slot_addr + 8 : slot_addr + 16]

            self.assertEqual(name_id, i + 1)
            self.assertEqual(status_flags, b"\x56\x08")
            self.assertEqual(active_flag, 1)
            self.assertEqual(level, 99)
            self.assertEqual(affection, 100)
            self.assertEqual(unpack_monster_stats(stat_bytes), (999, 999, 999, 999, 999, 999))

    def test_inject_monster_bank_invalid_slot(self):
        """Raises ValueError if target slot is not present in save."""
        sav = bytearray(0x10000)
        with self.assertRaises(ValueError):
            inject_monster_bank(sav, target_slot=0)

    def test_diagnostic_and_validation(self):
        """Inspect and validate routines correctly report the 20 captured monsters."""
        sav = self._create_mock_save()
        patched = inject_monster_bank(sav, target_slot=1)

        with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tf:
            tf.write(patched)
            tf_path = tf.name

        try:
            self.assertTrue(validate_save_file(tf_path, verbose=False))
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)


if __name__ == "__main__":
    unittest.main()
