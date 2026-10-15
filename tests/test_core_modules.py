"""Tests for the modularized core package."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core
import core.builder
import core.cli
import core.config
import core.patcher
import core.roster
import core.save
import ffta_tool


class TestCoreModules(unittest.TestCase):
    def test_core_package_exports(self):
        """Ensure all required symbols are exported directly by core."""
        expected = [
            "MAGIC",
            "SECTOR_SIZE",
            "atomic_write",
            "auto_detect_save",
            "clear_clan_cards",
            "compute_crc",
            "create_snapshot_backup",
            "display_roster",
            "equip_unit_build",
            "fix_crc",
            "get_default_backup_dir",
            "get_item_name",
            "get_slots",
            "inject_unit",
            "inspect_save",
            "load_builds",
            "load_config",
            "parse_simple_toml",
            "patch_clan_units",
            "patch_super_starter",
            "rename_unit",
            "resolve_job_and_race",
        ]
        for symbol in expected:
            self.assertTrue(hasattr(core, symbol), f"core is missing export: {symbol}")
            self.assertTrue(hasattr(ffta_tool, symbol), f"ffta_tool is missing export: {symbol}")

    def test_core_save_functions(self):
        """Ensure core.save exports primary save and wear-leveling functions."""
        self.assertEqual(core.save.SECTOR_SIZE, 0x1000)
        self.assertEqual(core.save.MAGIC, b"FFTEX000")
        self.assertTrue(callable(core.save.compute_crc))
        self.assertTrue(callable(core.save.get_slots))
        self.assertTrue(callable(core.save.atomic_write))

    def test_core_roster_functions(self):
        """Ensure core.roster exports diagnostics and roster functions."""
        self.assertTrue(callable(core.roster.get_item_name))
        self.assertTrue(callable(core.roster.inspect_save))
        self.assertTrue(callable(core.roster.display_roster))

    def test_core_builder_functions(self):
        """Ensure core.builder exports unit injection, building, and renaming."""
        self.assertTrue(callable(core.builder.inject_unit))
        self.assertTrue(callable(core.builder.equip_unit_build))
        self.assertTrue(callable(core.builder.rename_unit))
        self.assertTrue(callable(core.builder.resolve_job_and_race))

    def test_core_patcher_functions(self):
        """Ensure core.patcher exports clan patcher and super starter functions."""
        self.assertTrue(callable(core.patcher.patch_clan_units))
        self.assertTrue(callable(core.patcher.clear_clan_cards))
        self.assertTrue(callable(core.patcher.patch_super_starter))

    def test_core_cli_main(self):
        """Ensure core.cli exports main entry point."""
        self.assertTrue(callable(core.cli.main))
        self.assertTrue(callable(ffta_tool.main))


if __name__ == "__main__":
    unittest.main()
