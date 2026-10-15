#!/usr/bin/env python3
"""
Unit tests for Final Fantasy Tactics Advance Save Tool (ffta_tool)
"""

import os
import struct
import sys
import tempfile
import unittest

# Ensure parent directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ffta_tool import (
    MAGIC,
    RACE_JOB_COUNTERS,
    RECRUIT_NAMES,
    SECTOR_SIZE,
    atomic_write,
    auto_detect_save,
    clear_clan_cards,
    compute_crc,
    compute_god_stats,
    create_snapshot_backup,
    equip_unit_build,
    fix_crc,
    generate_random_name,
    get_default_backup_dir,
    get_name_id_by_str,
    get_slots,
    get_unit_name,
    inject_unit,
    load_builds,
    load_config,
    parse_simple_toml,
    patch_clan_units,
    patch_super_starter,
    rename_unit,
    resolve_job_and_race,
)


def create_mock_save():
    """Generates a minimal, valid 128KB mock FFTA save with Slot 1 and Slot 2."""
    buf = bytearray(SECTOR_SIZE * 16)

    # Slot 1: Sector 0 header, Seq 10, Sectors [0, 1, 2, 3]
    buf[0:8] = MAGIC
    buf[8:12] = struct.pack("<I", 10)  # Sequence counter
    buf[0x10] = 0  # Slot 1
    buf[0x12:0x16] = bytes([0, 1, 2, 3])
    buf[0x76:0x78] = struct.pack("<H", 5)  # 5 missions cleared

    # Slot 2: Sector 4 header, Seq 20, Sectors [4, 5, 6, 7]
    s4_off = 4 * SECTOR_SIZE
    buf[s4_off : s4_off + 8] = MAGIC
    buf[s4_off + 8 : s4_off + 12] = struct.pack("<I", 20)  # Sequence counter
    buf[s4_off + 0x10] = 1  # Slot 2
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
        buf[u_off + 0x06] = race  # Race ID
        buf[u_off + 0x07] = job  # Job ID
        buf[u_off + 0x09] = 5  # Level
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
        buf[s8_off + 0x10] = 1  # Slot 2
        buf[s8_off + 0x12 : s8_off + 0x16] = bytes([8, 9, 10, 11])

        # Write a newer Slot 2 header to sector 12 with seq 50
        s12_off = 12 * SECTOR_SIZE
        buf[s12_off : s12_off + 8] = MAGIC
        buf[s12_off + 8 : s12_off + 12] = struct.pack("<I", 50)  # Newer seq
        buf[s12_off + 0x10] = 1  # Slot 2
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
        self.assertTrue(
            all(patched[u0_off + 0x41 + i] == 0xE4 for i in range(140)),
            "Hume abilities mastered",
        )
        self.assertTrue(
            all(patched[u0_off + 0x9C + i] == 0xE4 for i in range(26)),
            "Hume Blue Magic mastered",
        )
        self.assertEqual(
            bytes(patched[u0_off + 0xF1 : u0_off + 0x106]),
            RACE_JOB_COUNTERS[1],
            "Hume job counters injected",
        )

        # Check Unit 1 (Bangaa)
        u1_off = hdr_off + 0x80 + 1 * 0x108
        self.assertTrue(
            all(patched[u1_off + 0x41 + i] == 0xE4 for i in range(76)),
            "Bangaa abilities mastered",
        )
        self.assertEqual(
            bytes(patched[u1_off + 0xF1 : u1_off + 0x106]),
            RACE_JOB_COUNTERS[2],
            "Bangaa job counters injected",
        )

        # Check Unit 2 (Nu Mou)
        u2_off = hdr_off + 0x80 + 2 * 0x108
        self.assertTrue(
            all(patched[u2_off + 0x41 + i] == 0xE4 for i in range(94)),
            "Nu Mou abilities mastered",
        )
        self.assertTrue(
            all(patched[u2_off + 0x93 + i] == 0xE4 for i in range(12)),
            "Nu Mou Morpher mastered",
        )
        self.assertEqual(
            bytes(patched[u2_off + 0xF1 : u2_off + 0x106]),
            RACE_JOB_COUNTERS[3],
            "Nu Mou job counters injected",
        )

        # Check Unit 3 (Viera)
        u3_off = hdr_off + 0x80 + 3 * 0x108
        self.assertTrue(
            all(patched[u3_off + 0x41 + i] == 0xE4 for i in range(84)),
            "Viera abilities mastered",
        )
        self.assertEqual(
            bytes(patched[u3_off + 0xF1 : u3_off + 0x106]),
            RACE_JOB_COUNTERS[4],
            "Viera job counters injected",
        )

        # Check Unit 4 (Moogle)
        u4_off = hdr_off + 0x80 + 4 * 0x108
        self.assertTrue(
            all(patched[u4_off + 0x41 + i] == 0xE4 for i in range(87)),
            "Moogle abilities mastered",
        )
        self.assertEqual(
            bytes(patched[u4_off + 0xF1 : u4_off + 0x106]),
            RACE_JOB_COUNTERS[5],
            "Moogle job counters injected",
        )

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

    def test_super_starter_safety_check_blocks_active_missions(self):
        """Verifies super_starter blocks saves with cleared missions unless force=True."""
        buf = bytearray(self.mock_data)
        # Slot 1 in mock_data has 5 missions cleared
        with self.assertRaises(ValueError) as ctx:
            patch_super_starter(buf, target_slot=0)
        self.assertIn("Pass --force to override", str(ctx.exception))

        # With force=True, patching succeeds and resets missions to 0
        patched = patch_super_starter(buf, target_slot=0, force=True)
        slots = get_slots(patched)
        self.assertEqual(slots[0]["missions"], 0)
        self.assertTrue(slots[0]["valid"])

    def test_fix_crc_repairs_corrupted_checksum(self):
        """Verifies fix_crc corrects a corrupt CRC byte."""
        buf = bytearray(self.mock_data)
        # Corrupt Slot 1 CRC
        buf[0x0C:0x10] = b"\xde\xad\xbe\xef"
        slots_before = get_slots(buf)
        self.assertFalse(slots_before[0]["valid"], "Slot 1 should be corrupt")

        # Fix CRC
        fixed = fix_crc(buf, target_slot=0)
        slots_after = get_slots(fixed)
        self.assertTrue(slots_after[0]["valid"], "Slot 1 CRC should be repaired")

    def test_clear_clan_cards(self):
        """Verifies clear_clan_cards zeroes out cards and pardons jailed units."""
        buf = bytearray(self.mock_data)
        s4_off = 4 * SECTOR_SIZE

        # Set fake cards and jail flags on Unit 0 and Unit 1 in Slot 2
        u0_off = s4_off + 0x80 + 0 * 0x108
        u1_off = s4_off + 0x80 + 1 * 0x108
        buf[u0_off + 0x102] = 1  # 1 Red Card
        buf[u0_off + 0x103] = 3  # 3 Yellow Cards
        buf[u0_off + 0x28] = 0x08  # Incarcerated in prison
        buf[u0_off + 0x101] = 0x03  # 3 battles remaining
        buf[u0_off + 0x104] = 0x03

        buf[u1_off + 0x103] = 2  # 2 Yellow Cards

        cleared = clear_clan_cards(buf, target_slot=1)
        slots = get_slots(cleared)
        self.assertTrue(slots[1]["valid"], "CRC must be valid after card clearing")
        self.assertEqual(cleared[u0_off + 0x102], 0, "Red cards cleared")
        self.assertEqual(cleared[u0_off + 0x103], 0, "Yellow cards cleared")
        self.assertEqual(cleared[u0_off + 0x28] & 0x08, 0, "Jail status cleared")
        self.assertEqual(cleared[u0_off + 0x101], 0, "Sentence battles cleared")
        self.assertEqual(cleared[u0_off + 0x104], 0xFF, "Unit state reset to free")
        self.assertEqual(cleared[u1_off + 0x102], 0, "Red cards cleared")
        self.assertEqual(cleared[u1_off + 0x103], 0, "Yellow cards cleared")

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
        self.assertEqual(get_item_name(0x002F), "Excalibur")
        self.assertEqual(get_item_name(0x0031), "Excalibur 2")
        self.assertEqual(get_item_name(0x005C), "Flamberge")
        self.assertEqual(get_item_name(0x0079), "White Staff")
        self.assertEqual(get_item_name(0x0086), "Dream Watcher")
        self.assertEqual(get_item_name(0x0088), "Firewheel Rod")
        self.assertEqual(get_item_name(0x009D), "Scorpion Tail")
        self.assertEqual(get_item_name(0x009E), "Zeus Mace")
        self.assertEqual(get_item_name(0x00CC), "Conch Shell")
        self.assertEqual(get_item_name(0x00FD), "Bronze Shield")
        self.assertEqual(get_item_name(0x00FE), "Round Shield")
        self.assertEqual(get_item_name(0x0114), "Ribbon")
        self.assertEqual(get_item_name(0x0115), "Feather Cap")
        self.assertEqual(get_item_name(0x0117), "Green Beret")
        self.assertEqual(get_item_name(0x011B), "Thief Hat")
        self.assertEqual(get_item_name(0x0122), "Iron Armor")
        self.assertEqual(get_item_name(0x012F), "Leather Garb")
        self.assertEqual(get_item_name(0x0132), "Survival Vest")
        self.assertEqual(get_item_name(0x0138), "Ninja Gear")
        self.assertEqual(get_item_name(0x0143), "Hempen Robe")

    def test_mappings_module(self):
        """Verifies modular mappings export expected tables and lengths."""
        import mappings

        self.assertEqual(len(mappings.RACE_NAMES), 5)
        self.assertIn(1, mappings.RACE_NAMES)
        self.assertEqual(mappings.RACE_NAMES[1], "Hume")
        self.assertEqual(mappings.JOB_NAMES[0x01], ("Soldier", "Hume"))
        self.assertEqual(mappings.JOB_NAMES[0x21], ("Archer", "Viera"))
        self.assertEqual(len(mappings.EQUIPMENT_IDS), 361)
        self.assertEqual(len(mappings.CONSUMABLE_IDS), 14)
        self.assertIn("KNOWN_ITEMS", mappings.__all__)

    def test_example_super_starter_save(self):
        """Verifies packaged example Super Starter save file integrity."""
        example_path = os.path.join(os.path.dirname(__file__), "..", "examples", "FFTA_Super_Starter.sav")
        self.assertTrue(os.path.exists(example_path), "Example save file must exist")

        with open(example_path, "rb") as f:
            data = f.read()

        slots = get_slots(data)
        self.assertIn(0, slots, "Slot 1 must exist")
        self.assertIn(1, slots, "Slot 2 must exist")
        self.assertTrue(slots[0]["valid"], "Slot 1 CRC must be valid")
        self.assertTrue(slots[1]["valid"], "Slot 2 CRC must be valid")
        self.assertEqual(slots[0]["missions"], 0, "Slot 1 missions must be 0")
        self.assertEqual(slots[1]["missions"], 0, "Slot 2 missions must be 0")

    def test_parse_simple_toml(self):
        """Verifies simple fallback TOML parser accurately parses sections and types."""
        toml_content = """
        # Comment line
        [paths]
        backup_dir = "/tmp/ffta_test_backups"
        search_paths = [
            "/path/one/*.sav",
            "/path/two/*.sav"
        ]

        [defaults]
        slot = 1
        equip_qty = 5
        item_qty = 50
        backup = false
        """
        parsed = parse_simple_toml(toml_content)
        self.assertEqual(parsed["paths"]["backup_dir"], "/tmp/ffta_test_backups")
        self.assertEqual(parsed["paths"]["search_paths"], ["/path/one/*.sav", "/path/two/*.sav"])
        self.assertEqual(parsed["defaults"]["slot"], 1)
        self.assertEqual(parsed["defaults"]["equip_qty"], 5)
        self.assertEqual(parsed["defaults"]["item_qty"], 50)
        self.assertFalse(parsed["defaults"]["backup"])

    def test_load_config_and_missing_file(self):
        """Verifies load_config reads valid config files and raises FileNotFoundError on missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = os.path.join(tmpdir, "test_config.toml")
            with open(cfg_file, "w", encoding="utf-8") as f:
                f.write("[defaults]\nslot = 1\nequip_qty = 20\n")

            loaded = load_config(cfg_file)
            self.assertEqual(loaded.get("defaults", {}).get("slot"), 1)
            self.assertEqual(loaded.get("defaults", {}).get("equip_qty"), 20)

            # Nonexistent path should raise FileNotFoundError
            with self.assertRaises(FileNotFoundError):
                load_config(os.path.join(tmpdir, "nonexistent.toml"))

    def test_custom_backup_dir_and_snapshot(self):
        """Verifies get_default_backup_dir and create_snapshot_backup respect custom dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = os.path.join(tmpdir, "custom_backups")
            resolved_dir = get_default_backup_dir(custom_dir)
            self.assertEqual(str(resolved_dir), custom_dir)

            test_save = os.path.join(tmpdir, "test.sav")
            with open(test_save, "wb") as f:
                f.write(self.mock_data)

            b_path = create_snapshot_backup(test_save, "test_action", backup_dir=custom_dir)
            self.assertTrue(os.path.exists(b_path))
            self.assertTrue(b_path.startswith(custom_dir))

    def test_auto_detect_save_with_config_search_paths(self):
        """Verifies auto_detect_save finds save files matching custom search_paths in config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "my_custom_game.sav")
            with open(save_path, "wb") as f:
                f.write(self.mock_data)

            cfg = {"paths": {"search_paths": [os.path.join(tmpdir, "*.sav")]}}
            detected = auto_detect_save(cfg)
            self.assertEqual(detected, save_path)

    def test_load_builds(self):
        """Verifies load_builds reads builds.toml correctly and handles missing files."""
        builds = load_builds()
        self.assertIn("gladiator", builds)
        self.assertIn("blue_mage", builds)
        self.assertIn("paladin", builds)
        self.assertEqual(builds["gladiator"]["name"], "Bangaa Gladiator")
        self.assertEqual(len(builds["gladiator"]["gear"]), 5)

        # Missing file returns empty dict
        empty = load_builds("/nonexistent/path/builds.toml")
        self.assertEqual(empty, {})

    def test_equip_unit_build(self):
        """Verifies equip_unit_build equips matching optimal gear and updates CRC."""
        buf = bytearray(self.mock_data)
        # Unit 1 in mock Slot 2 is Bangaa White Monk (Job 0x0E)
        u1_off = 4 * SECTOR_SIZE + 0x80 + 1 * 0x108
        # Clear gear first
        buf[u1_off + 0x2A : u1_off + 0x34] = bytes(10)

        patched = equip_unit_build(buf, target_slot=1, target_unit=1)
        slots = get_slots(patched)
        self.assertTrue(slots[1]["valid"], "CRC must be valid after equipping build")

        # White Monk gear: [0x00C8, 0x012B, 0x0111, 0x015C, 0x0169]
        expected_gear = struct.pack("<5H", 0x00C8, 0x012B, 0x0111, 0x015C, 0x0169)
        self.assertEqual(patched[u1_off + 0x2A : u1_off + 0x34], expected_gear)

    def test_clear_clan_cards_auto_re_equip(self):
        """Verifies clear_clan_cards pardons jailed unit and auto re-equips if naked."""
        buf = bytearray(self.mock_data)
        s4_off = 4 * SECTOR_SIZE
        u1_off = s4_off + 0x80 + 1 * 0x108

        # Incarcerate unit 1 and strip gear
        buf[u1_off + 0x28] = 0x08
        buf[u1_off + 0x101] = 0x03
        buf[u1_off + 0x104] = 0x03
        buf[u1_off + 0x2A : u1_off + 0x34] = bytes(10)

        cleared = clear_clan_cards(buf, target_slot=1, re_equip=True)
        slots = get_slots(cleared)
        self.assertTrue(slots[1]["valid"], "CRC must be valid after card clearing")
        self.assertEqual(cleared[u1_off + 0x28] & 0x08, 0, "Jail status cleared")
        self.assertEqual(cleared[u1_off + 0x104], 0xFF, "Unit state reset to free")

        # Gear should have been auto re-equipped from builds.toml
        expected_gear = struct.pack("<5H", 0x00C8, 0x012B, 0x0111, 0x015C, 0x0169)
        self.assertEqual(cleared[u1_off + 0x2A : u1_off + 0x34], expected_gear)

    def test_compute_god_stats(self):
        """Verifies compute_god_stats calculates optimal 115% top-rolled base stats and growths."""
        # Test Job 0x1A (Nu Mou Morpher) at Level 8
        stats = compute_god_stats(0x1A, level=8)
        self.assertEqual(stats["hp"], 86)
        self.assertEqual(stats["mp"], 56)
        self.assertEqual(stats["speed"], 137)
        self.assertEqual(stats["watk"], 130)
        self.assertEqual(stats["wdef"], 149)
        self.assertEqual(stats["mpow"], 140)
        self.assertEqual(stats["mres"], 148)

        # Test Job 0x22 (Viera Assassin) at Level 8
        stats_assassin = compute_god_stats(0x22, level=8)
        self.assertEqual(stats_assassin["speed"], 159)
        self.assertEqual(stats_assassin["hp"], 66)

    def test_name_helpers_and_generator(self):
        """Verifies get_unit_name, get_name_id_by_str, and generate_random_name."""
        self.assertEqual(len(RECRUIT_NAMES), 725)
        self.assertEqual(get_unit_name(0, special_flag=2), "Marche")
        self.assertEqual(get_unit_name(8, special_flag=8), "Montblanc")
        self.assertEqual(get_unit_name(2, special_flag=1), "Isaac")
        self.assertEqual(get_unit_name(156, special_flag=1), "Domenic")
        self.assertEqual(get_unit_name(545, special_flag=1), "Kudhos")

        self.assertEqual(get_name_id_by_str("Isaac"), 2)
        self.assertEqual(get_name_id_by_str("domenic"), 156)
        self.assertEqual(get_name_id_by_str("KUDHOS"), 545)
        self.assertIsNone(get_name_id_by_str("NonExistentNameXYZ"))

        # Verify Viera random name is within female pool (320..499)
        viera_id, viera_name = generate_random_name(race_id=4)
        self.assertTrue(320 <= viera_id < 500)
        self.assertEqual(viera_name, RECRUIT_NAMES[viera_id])

        # Verify excluded_ids prevents duplicate names
        excluded = {156}
        nu_mou_id, nu_mou_name = generate_random_name(race_id=3, excluded_ids=excluded)
        self.assertNotIn(nu_mou_id, excluded)

    def test_resolve_job_and_race(self):
        """Verifies resolve_job_and_race handles builds and job names."""
        # Build key from builds.toml
        j_id, r_id, gear, title = resolve_job_and_race("morpher")
        self.assertEqual(j_id, 0x1A)  # Morpher
        self.assertEqual(r_id, 3)  # Nu Mou
        self.assertEqual(gear[0], 0x00E8)  # Dragon Soul
        self.assertIn("Morpher", title)

        # Bangaa Dragoon
        j_id, r_id, gear, title = resolve_job_and_race("dragoon")
        self.assertEqual(j_id, 0x0E)
        self.assertEqual(r_id, 2)
        self.assertEqual(gear[0], 0x00C8)

        # Raw job name without build entry
        j_id, r_id, _, title = resolve_job_and_race("Bangaa Warrior")
        self.assertEqual(j_id, 0x0D)
        self.assertEqual(r_id, 2)

        with self.assertRaises(ValueError):
            resolve_job_and_race("invalid_job_xyz")

    def test_inject_unit_auto_slot_and_god_stats(self):
        """Verifies inject_unit auto-detects first free slot, sets god stats, mastered skills, and valid CRC."""
        buf = bytearray(self.mock_data)
        # Mock Slot 2 has units 0..4 occupied. Auto-detection should choose Unit 5.
        patched, info = inject_unit(buf, build_or_job="morpher", target_slot=1, level=8)

        self.assertEqual(info["unit_idx"], 5)
        self.assertEqual(info["race"], "Nu Mou")
        self.assertEqual(info["job"], "Morpher")
        self.assertEqual(info["level"], 8)
        self.assertEqual(info["stats"]["speed"], 137)

        slots = get_slots(patched)
        self.assertTrue(slots[1]["valid"], "CRC must be valid after injection")
        self.assertEqual(slots[1]["counter"], 21)

        # Check unit bytes in Slot 2 (Flash Sector 4)
        u5_off = 4 * SECTOR_SIZE + 0x80 + 5 * 0x108
        self.assertEqual(patched[u5_off + 0x04], 1)  # Special generic flag
        self.assertEqual(patched[u5_off + 0x05], 0x1A)  # Sprite index
        self.assertEqual(patched[u5_off + 0x06], 3)  # Race ID Nu Mou
        self.assertEqual(patched[u5_off + 0x07], 0x1A)  # Job ID Morpher
        self.assertEqual(patched[u5_off + 0x09], 8)  # Level 8

        # Check speed stat at 0xD2:0xD4
        spd = struct.unpack("<H", patched[u5_off + 0xD2 : u5_off + 0xD4])[0]
        self.assertEqual(spd, 137)

        # Check Primary A-Ability Set at 0x35 (30 = Morph) and Secondary at 0x36
        self.assertEqual(patched[u5_off + 0x35], 30)
        self.assertEqual(patched[u5_off + 0x36], 13)

        # Check abilities mastered (94 Nu Mou skills + 12 Morpher souls)
        self.assertTrue(all(patched[u5_off + 0x41 + i] == 0xE4 for i in range(94)))
        self.assertTrue(all(patched[u5_off + 0x93 + i] == 0xE4 for i in range(12)))

        # Check job unlock counters injected
        self.assertEqual(bytes(patched[u5_off + 0xF1 : u5_off + 0x101]), RACE_JOB_COUNTERS[3][:16])

        # Check unit state is active (0xFF)
        self.assertEqual(patched[u5_off + 0x104], 0xFF)

    def test_inject_unit_auto_level_clan_average(self):
        """Verifies inject_unit auto-calculates level based on clan average formula when level is None."""
        buf = bytearray(self.mock_data)
        # Mock Slot 2 has units 0..4 all at Lv 5. Clan average is 5.
        # Basic job (e.g. Soldier) gets clan average = 5.
        patched, info_soldier = inject_unit(buf, build_or_job="soldier", target_slot=1, target_unit=5, level=None)
        self.assertEqual(info_soldier["level"], 5)

        # Advanced job (e.g. Paladin) gets clan average + 1 = 6.
        patched, info_paladin = inject_unit(buf, build_or_job="paladin", target_slot=1, target_unit=6, level=None)
        self.assertEqual(info_paladin["level"], 6)

    def test_inject_unit_custom_name_and_slot(self):
        """Verifies inject_unit with explicit unit slot index and custom name from ROM."""
        buf = bytearray(self.mock_data)
        patched, info = inject_unit(
            buf,
            build_or_job="assassin",
            target_slot=1,
            target_unit=7,
            level=9,
            name="Lisa",
        )

        self.assertEqual(info["unit_idx"], 7)
        self.assertEqual(info["name"], "Lisa")
        self.assertEqual(info["name_id"], 478)
        self.assertEqual(info["job"], "Assassin")

        u7_off = 4 * SECTOR_SIZE + 0x80 + 7 * 0x108
        name_id = struct.unpack("<H", patched[u7_off : u7_off + 2])[0]
        self.assertEqual(name_id, 478)

    def test_inject_unit_clan_full_error(self):
        """Verifies inject_unit raises ValueError if all 24 slots are occupied and no slot specified."""
        buf = bytearray(self.mock_data)
        s4_off = 4 * SECTOR_SIZE
        # Mark all 24 units as level 1
        for u in range(24):
            buf[s4_off + 0x80 + u * 0x108 + 0x09] = 1

        with self.assertRaises(ValueError) as ctx:
            inject_unit(buf, build_or_job="morpher", target_slot=1)
        self.assertIn("Clan is full", str(ctx.exception))

    def test_rename_unit(self):
        """Verifies rename_unit updates Name ID, increments counter, and updates CRC."""
        buf = bytearray(self.mock_data)
        # Rename unit 2 (Nu Mou) in Slot 2 to Kudhos
        patched, new_name = rename_unit(buf, target_unit=2, new_name="Kudhos", target_slot=1)
        self.assertEqual(new_name, "Kudhos")

        u2_off = 4 * SECTOR_SIZE + 0x80 + 2 * 0x108
        name_id = struct.unpack("<H", patched[u2_off : u2_off + 2])[0]
        self.assertEqual(name_id, 545)

        slots = get_slots(patched)
        self.assertTrue(slots[1]["valid"], "CRC must be valid after renaming")

    @unittest.skipUnless(
        os.path.exists(
            os.environ.get(
                "FFTA_ROM_PATH",
                "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].gba",
            )
        ),
        "Local ROM file not present; skipping live ROM binary verification",
    )
    def test_optional_rom_verification(self):
        """Optionally validates embedded tables match local GBA ROM when present."""
        rom_path = os.environ.get(
            "FFTA_ROM_PATH",
            "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].gba",
        )
        with open(rom_path, "rb") as f:
            rom = f.read()

        # Verify pointer table has 725 names
        self.assertEqual(len(RECRUIT_NAMES), 725)

        # Verify first name (Arthur) and last name (Romark) match pointers
        tbl_start = 0x5680DC
        p0 = struct.unpack("<I", rom[tbl_start : tbl_start + 4])[0] - 0x08000000
        p_last = struct.unpack("<I", rom[tbl_start + 724 * 4 : tbl_start + 725 * 4])[0] - 0x08000000
        self.assertEqual(rom[p0 : p0 + 2], bytes([1, 177]))  # "Arthur"
        self.assertEqual(rom[p_last : p_last + 2], bytes([1, 194]))  # "Romark"


if __name__ == "__main__":
    unittest.main()
