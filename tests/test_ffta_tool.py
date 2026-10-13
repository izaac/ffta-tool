#!/usr/bin/env python3
"""
Unit tests for Final Fantasy Tactics Advance Save Tool (ffta_tool)
"""

import os
import sys
import struct
import tempfile
import unittest

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ffta_tool import (
    SECTOR_SIZE,
    MAGIC,
    RACE_JOB_COUNTERS,
    compute_crc,
    get_slots,
    patch_clan_units,
    patch_super_starter,
    fix_crc,
    create_snapshot_backup,
    atomic_write,
)


def create_mock_save():
    """Generates a minimal, valid 128KB mock FFTA save with Slot 1 and Slot 2."""
    buf = bytearray(SECTOR_SIZE * 16)

    # Slot 1: Sector 0 header, Seq 10, Sectors [0, 1, 2, 3]
    buf[0:8] = MAGIC
    buf[8:12] = struct.pack("<I", 10)  # Sequence counter
    buf[0x10] = 0                      # Slot 1
    buf[0x12:0x16] = bytes([0, 1, 2, 3])
    buf[0x76:0x78] = struct.pack("<H", 5)  # 5 missions cleared

    # Slot 2: Sector 4 header, Seq 20, Sectors [4, 5, 6, 7]
    s4_off = 4 * SECTOR_SIZE
    buf[s4_off : s4_off + 8] = MAGIC
    buf[s4_off + 8 : s4_off + 12] = struct.pack("<I", 20)  # Sequence counter
    buf[s4_off + 0x10] = 1                                 # Slot 2
    buf[s4_off + 0x12 : s4_off + 0x16] = bytes([4, 5, 6, 7])
    buf[s4_off + 0x76 : s4_off + 0x78] = struct.pack("<H", 0)

    # Populate 5 initial mock units in Slot 2 (one of each race)
    # Unit 0: Hume (Race 1), Job 0x01 (Soldier), Lv 5
    # Unit 1: Bangaa (Race 2), Job 0x0E (White Monk), Lv 4
    # Unit 2: Nu Mou (Race 3), Job 0x14 (White Mage), Lv 3
    # Unit 3: Viera (Race 4), Job 0x1C (Fencer), Lv 6
    # Unit 4: Moogle (Race 5), Job 0x27 (Thief), Lv 7
    races_and_jobs = [(1, 0x01), (2, 0x0E), (3, 0x14), (4, 0x1C), (5, 0x27)]
    for idx, (race, job) in enumerate(races_and_jobs):
        u_off = s4_off + 0x80 + idx * 0x108
        buf[u_off + 0x06] = race   # Race ID
        buf[u_off + 0x07] = job    # Job ID
        buf[u_off + 0x09] = 5      # Level
        # Mock equipment: Hand 1 = 0x0001, Hand 2 = 0x0110
        buf[u_off + 0x2A : u_off + 0x2E] = struct.pack("<2H", 0x0001, 0x0110)

    # Calculate and store valid CRCs
    crc1 = compute_crc(buf, [0, 1, 2, 3])
    buf[0x0C:0x10] = struct.pack("<I", crc1)

    crc2 = compute_crc(buf, [4, 5, 6, 7])
    buf[s4_off + 0x0C : s4_off + 0x10] = struct.pack("<I", crc2)

    return buf


class TestFftaTool(unittest.TestCase):
    """Test suite for FFTA save tool functions."""

    def setUp(self):
        self.mock_data = create_mock_save()

    def test_slot_detection_and_crc_validation(self):
        """Verifies get_slots accurately parses active slots and validates CRCs."""
        slots = get_slots(self.mock_data)
        self.assertIn(0, slots, "Slot 1 should be detected")
        self.assertIn(1, slots, "Slot 2 should be detected")

        # Slot 1 assertions
        s1 = slots[0]
        self.assertEqual(s1["header_sector"], 0)
        self.assertEqual(s1["counter"], 10)
        self.assertEqual(s1["sectors"], [0, 1, 2, 3])
        self.assertEqual(s1["missions"], 5)
        self.assertTrue(s1["valid"], "Slot 1 CRC should be valid")

        # Slot 2 assertions
        s2 = slots[1]
        self.assertEqual(s2["header_sector"], 4)
        self.assertEqual(s2["counter"], 20)
        self.assertEqual(s2["sectors"], [4, 5, 6, 7])
        self.assertEqual(s2["missions"], 0)
        self.assertTrue(s2["valid"], "Slot 2 CRC should be valid")

    def test_wear_leveling_highest_sequence_selection(self):
        """Verifies that the slot with the highest sequence counter wins."""
        buf = bytearray(self.mock_data)

        # Write an older Slot 2 header to sector 8 with seq 15
        s8_off = 8 * SECTOR_SIZE
        buf[s8_off : s8_off + 8] = MAGIC
        buf[s8_off + 8 : s8_off + 12] = struct.pack("<I", 15)  # Older seq
        buf[s8_off + 0x10] = 1                                 # Slot 2
        buf[s8_off + 0x12 : s8_off + 0x16] = bytes([8, 9, 10, 11])

        # Write a newer Slot 2 header to sector 12 with seq 50
        s12_off = 12 * SECTOR_SIZE
        buf[s12_off : s12_off + 8] = MAGIC
        buf[s12_off + 8 : s12_off + 12] = struct.pack("<I", 50)  # Newer seq
        buf[s12_off + 0x10] = 1                                  # Slot 2
        buf[s12_off + 0x12 : s12_off + 0x16] = bytes([12, 13, 14, 15])

        slots = get_slots(buf)
        self.assertEqual(slots[1]["header_sector"], 12)
        self.assertEqual(slots[1]["counter"], 50)

    def test_patch_clan_units_masters_all_races(self):
        """Verifies patch_clan_units masters all 5 races and injects job counters."""
        buf = bytearray(self.mock_data)
        patched = patch_clan_units(buf, target_slot=1)

        slots = get_slots(patched)
        s2 = slots[1]
        self.assertTrue(s2["valid"], "Patched slot must have valid CRC")
        self.assertEqual(s2["counter"], 21, "Sequence counter should be bumped by 1")

        hdr_off = s2["header_sector"] * SECTOR_SIZE

        # Check Unit 0 (Hume)
        u0_off = hdr_off + 0x80 + 0 * 0x108
        self.assertTrue(all(patched[u0_off + 0x41 + i] == 0xE4 for i in range(140)), "Hume abilities mastered")
        self.assertTrue(all(patched[u0_off + 0x9C + i] == 0xE4 for i in range(26)), "Hume Blue Magic mastered")
        self.assertEqual(bytes(patched[u0_off + 0xF1 : u0_off + 0x106]), RACE_JOB_COUNTERS[1], "Hume job counters injected")

        # Check Unit 1 (Bangaa)
        u1_off = hdr_off + 0x80 + 1 * 0x108
        self.assertTrue(all(patched[u1_off + 0x41 + i] == 0xE4 for i in range(76)), "Bangaa abilities mastered")
        self.assertEqual(bytes(patched[u1_off + 0xF1 : u1_off + 0x106]), RACE_JOB_COUNTERS[2], "Bangaa job counters injected")

        # Check Unit 2 (Nu Mou)
        u2_off = hdr_off + 0x80 + 2 * 0x108
        self.assertTrue(all(patched[u2_off + 0x41 + i] == 0xE4 for i in range(94)), "Nu Mou abilities mastered")
        self.assertTrue(all(patched[u2_off + 0x93 + i] == 0xE4 for i in range(12)), "Nu Mou Morpher mastered")
        self.assertEqual(bytes(patched[u2_off + 0xF1 : u2_off + 0x106]), RACE_JOB_COUNTERS[3], "Nu Mou job counters injected")

        # Check Unit 3 (Viera)
        u3_off = hdr_off + 0x80 + 3 * 0x108
        self.assertTrue(all(patched[u3_off + 0x41 + i] == 0xE4 for i in range(84)), "Viera abilities mastered")
        self.assertEqual(bytes(patched[u3_off + 0xF1 : u3_off + 0x106]), RACE_JOB_COUNTERS[4], "Viera job counters injected")

        # Check Unit 4 (Moogle)
        u4_off = hdr_off + 0x80 + 4 * 0x108
        self.assertTrue(all(patched[u4_off + 0x41 + i] == 0xE4 for i in range(87)), "Moogle abilities mastered")
        self.assertEqual(bytes(patched[u4_off + 0xF1 : u4_off + 0x106]), RACE_JOB_COUNTERS[5], "Moogle job counters injected")

        # Verify gear was NOT clobbered
        w1, w2 = struct.unpack("<2H", patched[u0_off + 0x2A : u0_off + 0x2E])
        self.assertEqual(w1, 0x0001, "Hand 1 weapon preserved")
        self.assertEqual(w2, 0x0110, "Hand 2 weapon/shield preserved")

    def test_idempotent_skip_for_already_mastered_units(self):
        """Verifies running patch_clan_units again skips already mastered units."""
        buf = bytearray(self.mock_data)
        # Patch once
        buf = patch_clan_units(buf, target_slot=1)

        # Patch twice
        seq_before = get_slots(buf)[1]["counter"]
        buf2 = patch_clan_units(buf, target_slot=1)
        seq_after = get_slots(buf2)[1]["counter"]

        self.assertEqual(seq_after, seq_before + 1, "Counter increments cleanly")
        self.assertTrue(get_slots(buf2)[1]["valid"], "CRC stays valid")

    def test_targeted_single_unit_patch(self):
        """Verifies patching a specific unit index via target_unit."""
        buf = bytearray(self.mock_data)
        # Target only unit 4 (Moogle)
        buf = patch_clan_units(buf, target_slot=1, target_unit=4)

        hdr_off = 4 * SECTOR_SIZE
        u4_off = hdr_off + 0x80 + 4 * 0x108
        u0_off = hdr_off + 0x80 + 0 * 0x108

        # Moogle should be mastered
        self.assertTrue(all(buf[u4_off + 0x41 + i] == 0xE4 for i in range(87)))
        # Hume (Unit 0) should remain unmastered
        self.assertFalse(all(buf[u0_off + 0x41 + i] == 0xE4 for i in range(140)))

    def test_super_starter_patch(self):
        """Verifies super_starter sets gear, consumables, 0 missions, and valid CRC."""
        buf = bytearray(self.mock_data)
        buf = patch_super_starter(buf, target_slot=1, equip_qty=10, item_qty=99, counter_bump=60)

        slots = get_slots(buf)
        s2 = slots[1]
        self.assertTrue(s2["valid"], "Super starter CRC must be valid")
        self.assertEqual(s2["missions"], 0, "Missions cleared must be 0")
        self.assertGreaterEqual(s2["counter"], 60, "Sequence counter bumped")

        # Verify inventory in Sector 5 (Sector 1 of Slot 2)
        sec5_off = 5 * SECTOR_SIZE
        # Check first equipment item (ID 1)
        item1_id = int.from_bytes(buf[sec5_off + 0x940 : sec5_off + 0x942], "little")
        item1_qty = buf[sec5_off + 0x942]
        self.assertEqual(item1_id, 1)
        self.assertEqual(item1_qty, 10)

        # Check first consumable (ID 0x16A)
        c1_id = int.from_bytes(buf[sec5_off + 0xEE4 : sec5_off + 0xEE6], "little")
        c1_qty = buf[sec5_off + 0xEE6]
        self.assertEqual(c1_id, 0x16A)
        self.assertEqual(c1_qty, 99)

    def test_fix_crc_repairs_corrupted_checksum(self):
        """Verifies fix_crc corrects a corrupt CRC byte."""
        buf = bytearray(self.mock_data)
        # Corrupt Slot 1 CRC
        buf[0x0C:0x10] = b"\xDE\xAD\xBE\xEF"
        slots_before = get_slots(buf)
        self.assertFalse(slots_before[0]["valid"], "Slot 1 should be corrupt")

        # Fix CRC
        fixed = fix_crc(buf, target_slot=0)
        slots_after = get_slots(fixed)
        self.assertTrue(slots_after[0]["valid"], "Slot 1 CRC should be repaired")

    def test_atomic_write_and_snapshot_backup(self):
        """Verifies atomic_write and snapshot backup behavior."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_save.sav")
            with open(test_file, "wb") as f:
                f.write(self.mock_data)

            # Test atomic write
            modified_data = bytearray(self.mock_data)
            modified_data[0x20] = 0xAA
            atomic_write(test_file, modified_data)

            with open(test_file, "rb") as f:
                re_read = f.read()
            self.assertEqual(re_read[0x20], 0xAA, "Atomic write should persist modifications")

            # Test snapshot backup
            backup_file = create_snapshot_backup(test_file, "test_action")
            self.assertTrue(os.path.exists(backup_file), "Backup file must exist")
            self.assertEqual(os.path.getsize(backup_file), len(self.mock_data))

    def test_item_resolution(self):
        """Verifies KNOWN_ITEMS resolves equipment names accurately."""
        from ffta_tool import get_item_name
        self.assertEqual(get_item_name(0), "-")
        self.assertEqual(get_item_name(0x0026), "Tulwar")
        self.assertEqual(get_item_name(0x0029), "Apocalypse")
        self.assertEqual(get_item_name(0x0031), "Excalibur")
        self.assertEqual(get_item_name(0x005C), "Flamberge")
        self.assertEqual(get_item_name(0x0086), "Dream Watcher")
        self.assertEqual(get_item_name(0x0088), "Firewheel Rod")
        self.assertEqual(get_item_name(0x00CC), "Conch Shell")
        self.assertEqual(get_item_name(0x00FD), "Bronze Shield")
        self.assertEqual(get_item_name(0x00FE), "Round Shield")
        self.assertEqual(get_item_name(0x0114), "Ribbon")
        self.assertEqual(get_item_name(0x0115), "Feather Cap")
        self.assertEqual(get_item_name(0x0117), "Green Beret")
        self.assertEqual(get_item_name(0x011B), "Thief Hat")
        self.assertEqual(get_item_name(0x0122), "Iron Armor")
        self.assertEqual(get_item_name(0x0132), "Survival Vest")
        self.assertEqual(get_item_name(0x0138), "Ninja Gear")


if __name__ == "__main__":
    unittest.main()
