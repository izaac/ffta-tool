# Final Fantasy Tactics Advance (GBA) Save Tool

A simple, standalone tool to inspect, backup, and patch *Final Fantasy Tactics Advance* save files for handheld consoles (NextUI, Miyoo, Anbernic) and PC emulators.

Zero external dependencies required. Built purely with the standard Python library.

---

## Installation

Works on **any Linux, macOS, or Windows** system with Python 3.8+:

### Linux & macOS

```bash
git clone https://github.com/izaac/ffta-tool.git
cd ffta-tool
chmod +x ffta_tool.py
```

*(Optional: Copy to `~/.local/bin/ffta-tool` to run from anywhere).*

### Windows

1. Download and install [Python 3](https://www.python.org/downloads/) (check the box: *"Add Python to PATH"* during install).
2. Clone or download this repository.
3. Open Command Prompt or PowerShell in the folder:

```powershell
python ffta_tool.py
```

---

## Usage

```bash
# 1. View Clan Roster & Save Health (Auto-detects SD card or local save)
python3 ffta_tool.py

# 2. Master skills & unlock advanced jobs for new recruits (e.g. Juggler, Gunner)
python3 ffta_tool.py --patch-units

# 3. Create an instant timestamped backup
python3 ffta_tool.py --backup

# 4. Super Starter: 10x all 361 weapons & 99x consumables on Slot 2
python3 ffta_tool.py --super-starter --slot 2

# 5. Fix corrupt save checksum (CRC32)
python3 ffta_tool.py path/to/save.sav --fix-crc --slot 2
```

---

## Testing

Run built-in tests:

```bash
python3 -m unittest discover -s tests
```

---

## Handheld Note

Close or exit the emulator on your handheld before replacing or updating save files on the SD card so the device loads fresh data from disk.
