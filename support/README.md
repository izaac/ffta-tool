# FFTA Tool Support & Diagnostics Suite

High-value automation and inspection scripts for *Final Fantasy Tactics Advance* (GBA) wear-leveled save files, ROM tables, and Analogue Pocket deployment.

---

## 🛠️ Tools Overview

| Script | Purpose | Key Flags |
| --- | --- | --- |
| [`validate_saves.py`](validate_saves.py) | Full health check across local and Pocket `.sav` files (CRCs, counters, units, equipment, duplicate skills, sprite glitches). | `--pocket`, `--all`, `[path]` |
| [`topup_clan_units.py`](topup_clan_units.py) | Non-destructive clan unit top-up (preserves high speed, buffs sub-optimal stats to 115% god roll, equips meta gear). | `--slot`, `--units`, `--sync` |
| [`generate_race_save.py`](generate_race_save.py) | Generates canonical race-specific `.sav` and `.gba` (Hume, Bangaa, Moogle, Viera, Nu Mou) with Lv 8 god stats and meta gear. | `<race>`, `--level`, `--sync` |
| [`sync_pocket.py`](sync_pocket.py) | Syncs canonical ROMs and saves to Analogue Pocket SD card with MD5 deduplication and OS filesystem flushing (`sync`). | `-n` (`--dry-run`), `--pocket` |
| [`inspect_rom.py`](inspect_rom.py) | Inspects ROM base stats/growths (`0x521A80`), item IDs, recruit names, and race ability mappings. | `--job`, `--item`, `--name`, `--races` |
| [`fix_save_crc.py`](fix_save_crc.py) | Recalculates and repairs Sector 0 / Sector 1 CRC32 checksums for both save slots without altering unit data. | `<path>` |

---

## 🚀 Quick Usage Examples

### 1. Save Health Check & Diagnostics

```bash
# Validate all local and Pocket saves
uv run python support/validate_saves.py

# Check only Analogue Pocket SD card saves
uv run python support/validate_saves.py --pocket

# Inspect a specific save file
uv run python support/validate_saves.py "/home/izaac/Documents/FFTA_Assets/Final Fantasy Tactics Advance (Bangaa).sav"
```

### 2. Generate Race Save Fleets

```bash
# Generate single race fleet (e.g. Nu Mou) and sync directly to Analogue Pocket
uv run python support/generate_race_save.py nu_mou --sync

# Generate all 5 canonical race fleets (Hume, Bangaa, Moogle, Viera, Nu Mou)
uv run python support/generate_race_save.py all --sync
```

### 3. Sync to Analogue Pocket SD Card

```bash
# Preview what would be copied
uv run python support/sync_pocket.py --dry-run

# Execute full copy and sync
uv run python support/sync_pocket.py
```

### 4. ROM & Database Inspection

```bash
# View base stats and growth rates for a job
uv run python support/inspect_rom.py --job "Sage"

# Search item database for weapon/armor IDs
uv run python support/inspect_rom.py --item "Ebon Blade"

# Look up recruit names for a specific race
uv run python support/inspect_rom.py --race "Nu Mou"

# Print all race configurations and default secondary ability sets
uv run python support/inspect_rom.py --races
```

### 5. Repair Save Checksums

```bash
# Repair CRC32 checksums on an altered save
uv run python support/fix_save_crc.py path/to/corrupted.sav
```
