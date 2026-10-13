# Final Fantasy Tactics Advance (GBA) Save Tool

A simple, standalone tool to inspect, backup, and patch *Final Fantasy Tactics Advance* save files for handheld consoles (NextUI, Miyoo, Anbernic) and PC emulators.

Zero external dependencies required. Built purely with the standard Python library.

---

## Installation

Works on **any Linux, macOS, or Windows** system with Python 3.10+:

### Quick Install (Pip)

Install locally to add the `ffta-tool` command to your environment:

```bash
git clone https://github.com/izaac/ffta-tool.git
cd ffta-tool
pip install -e .
```

### Standalone (No Install)

```bash
chmod +x ffta_tool.py
./ffta_tool.py
```

On Windows, install [Python 3](https://www.python.org/downloads/) (check *"Add Python to PATH"*), open Command Prompt in the folder, and run:

```powershell
python ffta_tool.py
```

---

## Usage

You can use either `ffta-tool` or `python3 ffta_tool.py`:

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

## Testing & Linting

Run built-in tests:

```bash
python3 -m unittest discover -s tests
```

Check code style with Ruff:

```bash
ruff check && ruff format --check
```

---

## Handheld Note

Close or exit the emulator on your handheld before replacing or updating save files on the SD card so the device loads fresh data from disk.
