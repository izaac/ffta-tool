# Final Fantasy Tactics Advance (GBA) Save Tool

Standalone utility to inspect, backup, and patch *Final Fantasy Tactics Advance* (GBA) Flash 64K / 128K wear-leveled save files for handheld consoles (Analogue Pocket, Miyoo, Anbernic) and PC emulators.

Zero external dependencies required. Built with Python 3.10+ standard library.

---

## Documentation Links

- [Clan Strategy & Equipment Metagame](docs/clan-strategy.md): Build rationale, combat gear upgrades, and MP mechanics.
- [Save Architecture & Internals](docs/save-architecture.md): Flash wear-leveling, CRC32, and 0x108 unit memory layout.
- [Analogue Pocket & Handheld Guide](docs/pocket-and-handhelds.md): openFPGA folder layouts and sync best practices.
- [Support & Diagnostics Suite](support/README.md): Automated save validator, race fleet generator, and Pocket syncer.

---

## Quick Start (with `uv`)

Run directly without installation:

```bash
uv run ffta-tool
```

Install as an isolated CLI command:

```bash
uv tool install .
ffta-tool
```

---

## Standalone (No `uv`)

Works on Linux, macOS, and Windows with Python 3.10+:

```bash
chmod +x ffta_tool.py
./ffta_tool.py
```

---

## CLI Commands & Flags

```bash
# View clan roster and save health (auto-detects save file)
ffta-tool

# Master abilities and unlock advanced jobs for recruits
ffta-tool --patch-units

# Target specific recruit index (0..23)
ffta-tool --patch-units --unit 5

# Create timestamped snapshot backup
ffta-tool --backup

# Apply Super Starter package (10x all 361 weapons and 99x consumables)
ffta-tool --super-starter --slot 2

# Clear yellow and red cards and pardon jailed units
ffta-tool --clear-cards --slot 2

# Repair corrupt CRC32 checksum
ffta-tool path/to/save.sav --fix-crc --slot 2
```

---

## Support Automation Suite

Automated diagnostic and fleet management scripts live in `support/`:

```bash
# 1. Full save health check across local and Pocket saves
uv run python support/validate_saves.py

# 2. Non-destructive clan unit top-up (preserves high speed, maxes stats and meta gear)
uv run python support/topup_clan_units.py --sync

# 3. Generate canonical race fleets (Hume, Bangaa, Moogle, Viera, Nu Mou)
uv run python support/generate_race_save.py nu_mou --sync

# 4. Sync ROMs and saves to Analogue Pocket SD card
uv run python support/sync_pocket.py

# 5. Inspect ROM tables, job growths, item stats, and recruit names
uv run python support/inspect_rom.py --job "Sage"
```

---

## Configuration (`config.toml`)

Copy `config.example.toml` to `config.toml` or `~/.config/ffta-tool/config.toml`:

```toml
[paths]
backup_dir = "~/Documents/FFTA_Backups"
search_paths = [
    "/run/media/*/*/Saves/GBA/*Final Fantasy Tactics Advance*.sav",
    "~/Documents/FFTA_Backups/*.sav",
    "*.sav",
]

[defaults]
slot = 2
equip_qty = 10
item_qty = 99
backup = true
```

---

## Verification & Tests

Run test suite:

```bash
uv run python -m unittest discover -s tests
```

Check code style:

```bash
uvx ruff check .
```
