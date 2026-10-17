# mGBA Headless Debugging & Automated Save Verification

This guide outlines how to perform automated, headless emulation tests of Final Fantasy
Tactics Advance (FFTA) GBA save files using **mGBA**, **Xvfb**, and **xdotool**. This
setup enables verifying save integrity, save slot selection menus, world map loading,
and party unit roster rendering in CI pipelines or terminal-only environments.

---

## 1. Architecture & Overview

Modifying FFTA saves (such as editing clan units, injecting Cyril Monster Bank beasts,
or equipping advanced job gear) requires verifying both raw CRC32 validity and in-game
engine acceptance:

1. **Save Slot Metadata**: Verifies that the game parses the save counter, clan name,
   cleared missions, and playtime without marking the slot as corrupted.
2. **World Map Transition**: Confirms that loading Slot 1 or Slot 2 transitions smoothly
   to the world map (Sprohm) without crashing or hanging.
3. **Party Roster Rendering**: Confirms that opening the Clan Unit Roster renders all
   party units, job sprites, and equipment without triggering soft-locks or graphical
   glitches.

The headless runner automates this by:

- Spawning an isolated virtual X11 framebuffer (`Xvfb`) on a dedicated display (e.g. `:99`).
- Booting `mgba` using dummy audio (`SDL_AUDIODRIVER=dummy`) and software rendering
  under X11 (`SDL_VIDEODRIVER=x11`).
- Driving title screen navigation and menu choices programmatically via `xdotool`.
- Capturing full-screen and cropped verification screenshots using ImageMagick (`import` / `magick`).

---

## 2. Prerequisites & Dependencies

The runner requires the following tools available in `PATH` (or specified via environment
variable overrides):

- **mGBA** (CLI or Qt): Game Boy Advance emulator.
- **xdotool**: X11 automation tool for programmatic keypresses.
- **Xvfb** (`xorg-server`): Virtual framebuffer X server.
- **ImageMagick** (`magick` or `convert`, `import`): For screen capture and cropping.

### Installation

#### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install -y mgba-sdl xdotool xvfb imagemagick
```

#### Arch Linux

```bash
sudo pacman -S mgba-sdl xdotool xorg-server-xvfb imagemagick
```

#### Nix / NixOS

You can run directly within an ad-hoc Nix shell:

```bash
nix-shell -p mgba xdotool xorg-server imagemagick
```

The runner script (`run_headless_test.sh`) includes automatic fallback to `nix-shell`
if tools are missing from the host environment on NixOS.

---

## 3. Keyboard Mappings

The automated runner interfaces with mGBA's default SDL input mapping:

- **A Button**: `x`
- **B Button**: `z`
- **L Button**: `a`
- **R Button**: `s`
- **Start Button**: `Return`
- **Select Button**: `BackSpace`
- **D-Pad**: `Up`, `Down`, `Left`, `Right`

---

## 4. Running Headless Tests

Use the automated test runner script located at `examples/mgba/run_headless_test.sh`:

```bash
./examples/mgba/run_headless_test.sh <path_to_rom.gba> [path_to_save.sav] [output_dir]
```

Or run via `just`:

```bash
just mgba-test path/to/rom.gba
```

### Parameters

- `<path_to_rom.gba>`: Path to a clean North American or European FFTA GBA ROM (required).
- `[path_to_save.sav]`: Path to the 64 KiB or 128 KiB `.sav` file to verify (optional;
  defaults to `examples/FFTA_Super_Starter.sav`).
- `[output_dir]`: Output directory for generated PNG screenshots (optional; defaults to
  `examples/mgba/output`).

### Environment Variable Overrides

If binaries are located in custom locations, override them using environment variables:

```bash
MGBA_BIN=/usr/local/bin/mgba \
XDOTOOL_BIN=/usr/bin/xdotool \
./examples/mgba/run_headless_test.sh path/to/game.gba
```

---

## 5. Interpreting Test Artifacts

The runner captures four verification screenshots in the output directory:

| Artifact | Verification Purpose |
| :--- | :--- |
| `title_screen.png` | Confirms GBA BIOS and FFTA boot cleanly to Title screen. |
| `slots_screen.png` | Confirms Save Slot metadata (Marche level, playtime, missions). |
| `world_map.png` | Confirms save loaded successfully into Sprohm on the world map. |
| `unit_roster.png` | Confirms Clan Unit Roster renders units, jobs, and equipment. |

### Visual Verification Criteria

1. **Save Slot Screen**:
   - Confirms Slot 1 displays valid Marche level, clan name, cleared missions, and playtime.
   - Verifies the save counter was accepted by the engine without corruption warnings.
2. **World Map**:
   - Confirms the map loads into Sprohm with correct clan funds and world calendar.
3. **Unit Roster**:
   - Confirms Marche, Montblanc, and clan members appear with expected sprites, jobs, and stats.
