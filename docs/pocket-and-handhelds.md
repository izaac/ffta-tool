# Analogue Pocket & Handheld Deployment Guide

Deployment instructions and best practices for running modified *Final Fantasy Tactics Advance* saves and ROMs on physical hardware.

---

## 1. Analogue Pocket (openFPGA)

The Analogue Pocket runs GBA titles via openFPGA cores (e.g. `Spirited.GBA`).

### Directory Layout

```text
POCKET/ (SD Root)
├── Assets/
│   └── gba/
│       └── common/
│           ├── Final Fantasy Tactics Advance (Hume).gba
│           ├── Final Fantasy Tactics Advance (Bangaa).gba
│           ├── Final Fantasy Tactics Advance (Moogle).gba
│           ├── Final Fantasy Tactics Advance (Viera).gba
│           ├── Final Fantasy Tactics Advance (Nu Mou).gba
│           └── Final Fantasy Tactics Advance (U) [!].gba
└── Saves/
    └── gba/
        ├── common/
        │   └── *.sav (Secondary/mirror lookup path)
        └── *.sav (Primary save lookup path)
```

### Automated Synchronization

Use the built-in tool in `support/`:

```bash
# Preview changes without writing
uv run python support/sync_pocket.py --dry-run

# Execute full copy and OS buffer flush
uv run python support/sync_pocket.py
```

`sync_pocket.py` automatically:

1. Compares MD5 hashes to avoid unnecessary writes to SD flash.
2. Deploys saves to both `/Saves/gba/` and `/Saves/gba/common/`.
3. Issues an OS `sync` call to flush all write caches before you eject the SD card.

---

## 2. Other Handhelds (Miyoo Mini, Anbernic, Steam Deck)

### OnionOS / GarlicOS / NextUI

- **ROM Path**: `Roms/GBA/`
- **Save Path**: `Saves/CurrentProfile/saves/GBA/` or adjacent to the ROM depending on retroarch core settings.
- **Naming Rule**: Save file stem must match the ROM file stem exactly (e.g. `FFTA.gba` -> `FFTA.sav`).

### Critical Safety Tips

- **Exit Emulator Before Syncing**: Always exit the running game/core on your handheld before swapping the SD card or copying saves. Emulators hold save state in RAM and will overwrite disk files on exit.
- **Always Flush Buffers**: On Linux/macOS, always run `sync` in terminal or click "Safely Remove / Eject" before pulling the SD card. FAT32 and exFAT filesystems will corrupt if unmounted mid-flush.
