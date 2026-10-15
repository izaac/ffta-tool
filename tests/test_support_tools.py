"""Unit tests for FFTA support and diagnostics tools."""

import os
import tempfile
import unittest

from support.fix_save_crc import fix_file_crc
from support.generate_race_save import generate_race_fleet
from support.inspect_rom import inspect_items, inspect_jobs, inspect_names, inspect_races
from support.sync_pocket import get_file_md5, sync_file
from support.validate_saves import validate_save_file


class TestSupportTools(unittest.TestCase):
    """Verifies that support and diagnostics tools execute reliably."""

    def test_inspect_rom_functions(self):
        """Ensures inspect_rom functions run without throwing errors."""
        inspect_jobs("Sage")
        inspect_jobs("all")
        inspect_items("Ebon Blade")
        inspect_names(race_name="Nu Mou")
        inspect_races()

    def test_sync_pocket_helpers(self):
        """Verifies MD5 calculation and sync_file helper."""
        with tempfile.NamedTemporaryFile(delete=False) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            f1.write(b"TestContent1")
            f2.write(b"TestContent2")
            p1, p2 = f1.name, f2.name

        try:
            self.assertNotEqual(get_file_md5(p1), get_file_md5(p2))
            copied = sync_file(p1, p2, dry_run=True)
            self.assertTrue(copied)
        finally:
            if os.path.exists(p1):
                os.remove(p1)
            if os.path.exists(p2):
                os.remove(p2)

    def test_generate_race_fleet_temp(self):
        """Verifies fleet generator for Nu Mou into a temporary directory."""
        base_sav = "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].sav"
        base_rom = "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].gba"
        if not os.path.exists(base_sav) or not os.path.exists(base_rom):
            self.skipTest("Base assets not found in environment.")

        with tempfile.TemporaryDirectory() as tmpdir:
            sav_path, gba_path = generate_race_fleet(
                race_key="nu_mou",
                base_sav_path=base_sav,
                base_rom_path=base_rom,
                output_dir=tmpdir,
                target_slot=1,
                level=8,
                sync=False,
            )
            self.assertTrue(os.path.exists(sav_path))
            self.assertTrue(os.path.exists(gba_path))
            self.assertTrue(validate_save_file(sav_path, verbose=False))
            self.assertTrue(fix_file_crc(sav_path))

    def test_topup_clan_units_temp(self):
        """Verifies topup_save on a temporary copy of base save."""
        import shutil

        from support.topup_clan_units import topup_save

        base_sav = "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (U) [!].sav"
        if not os.path.exists(base_sav):
            self.skipTest("Base save not found in environment.")

        with tempfile.TemporaryDirectory() as tmpdir:
            copy_path = os.path.join(tmpdir, "test_topup.sav")
            shutil.copy2(base_sav, copy_path)
            res = topup_save(save_path=copy_path, target_slot=1, target_units=[2, 3], sync=False)
            self.assertTrue(res)
            self.assertTrue(validate_save_file(copy_path, verbose=False))


if __name__ == "__main__":
    unittest.main()
