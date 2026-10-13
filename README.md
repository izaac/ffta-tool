# Final Fantasy Tactics Advance (GBA) Save Tool

A simple, standalone tool to inspect, backup, and patch *Final Fantasy Tactics Advance* save files for handheld consoles (NextUI, Miyoo, Anbernic) and PC emulators.

Zero external dependencies required. Built purely with the standard Python library.

---

## Quick Start (with `uv`)

Run instantly without installing or touching system Python:

```bash
git clone https://github.com/izaac/ffta-tool.git
cd ffta-tool
uv run ffta-tool
```

Or install as an isolated CLI command into user space:

```bash
uv tool install .
ffta-tool
```

---

## Standalone (No `uv`)

Works on **any Linux, macOS, or Windows** system with Python 3.10+:

### Linux & macOS

```bash
chmod +x ffta_tool.py
./ffta_tool.py
```

### Windows

1. Download and install [Python 3](https://www.python.org/downloads/) (check *"Add Python to PATH"* during install).
2. Clone or download this repository.
3. Open Command Prompt or PowerShell in the folder:

```powershell
python ffta_tool.py
```

---

## Usage

You can use either `ffta-tool` (via uv) or `./ffta_tool.py`:

```bash
# 1. View Clan Roster & Save Health (Auto-detects SD card or local save)
ffta-tool

# 2. Master skills & unlock advanced jobs for all clan recruits
ffta-tool --patch-units

# 3. Target a single recruit by unit index (0..23)
ffta-tool --patch-units --unit 5

# 4. Create an instant timestamped backup
ffta-tool --backup

# 5. Apply Super Starter package (10x all 361 weapons & 99x consumables)
ffta-tool --super-starter --slot 2

# 6. Fix corrupt save checksum (CRC32)
ffta-tool path/to/save.sav --fix-crc --slot 2
```

---

## Example Starter Save

A pristine demonstration save file is included in `examples/FFTA_Super_Starter.sav`:

- **Slot 1 & Slot 2**: Clean Cyril starter pub state with 0 missions cleared.
- **Roster**: 6 starting recruits with all skills mastered and valid job unlock tables.
- **Inventory**: 10x all 361 weapons and equipment, 99x all consumables.
- **Checksums**: Fully verified internal CRC32 on both slots.

---

## Testing & Development

Run built-in tests:

```bash
uv run python -m unittest discover -s tests
```

Check code style with Ruff:

```bash
uvx ruff check && uvx ruff format --check
```

---

## Handheld Note

Close or exit the emulator on your handheld before replacing or updating save files on the SD card so the device loads fresh data from disk.
