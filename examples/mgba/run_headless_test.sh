#!/usr/bin/env bash
# Headless mGBA automated verification runner for FFTA (GBA) saves.
#
# Launches an isolated Xvfb display, boots mGBA with a specified ROM and
# save file, automates UI navigation via xdotool, and captures title,
# save slot preview, world map, and clan unit roster screenshots to verify
# save integrity and stability.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Resolve binary paths portably from PATH or environment overrides
MGBA="${MGBA_BIN:-$(command -v mgba 2>/dev/null || true)}"
XDOTOOL="${XDOTOOL_BIN:-$(command -v xdotool 2>/dev/null || true)}"
XVFB="${XVFB_BIN:-$(command -v Xvfb 2>/dev/null || true)}"
MAGICK="${MAGICK_BIN:-$(command -v magick 2>/dev/null || command -v convert 2>/dev/null || true)}"
IMPORT="${IMPORT_BIN:-$(command -v import 2>/dev/null || true)}"

# If on NixOS and tools are missing from PATH, auto re-exec within nix-shell
if { [ -z "${MGBA}" ] || [ -z "${XDOTOOL}" ] || [ -z "${XVFB}" ]; } && command -v nix-shell >/dev/null 2>&1; then
    if [ "${NIX_SHELL_ACTIVE:-0}" -ne 1 ]; then
        echo "[*] Missing mGBA/Xvfb/xdotool in PATH. Re-running inside nix-shell environment..."
        export NIX_SHELL_ACTIVE=1
        cmd=$(printf '%q ' "$0" "$@")
        exec nix-shell -p mgba xdotool xorg-server imagemagick --run "$cmd"
    fi
fi

# Validation check for required tools
missing=()
[ -z "${MGBA}" ] && missing+=("mgba")
[ -z "${XDOTOOL}" ] && missing+=("xdotool")
[ -z "${XVFB}" ] && missing+=("Xvfb (xorg-server)")
[ -z "${MAGICK}" ] && missing+=("ImageMagick (magick/convert)")
[ -z "${IMPORT}" ] && missing+=("ImageMagick (import)")

if [ ${#missing[@]} -gt 0 ]; then
    echo "[!] Error: Missing required dependencies: ${missing[*]}" >&2
    echo "    Install them via your system package manager, or run with nix-shell:" >&2
    echo "    nix-shell -p mgba xdotool xorg-server imagemagick" >&2
    exit 1
fi

# Resolve ROM path: argument -> env -> config.toml -> common search paths
ROM_PATH="${1:-${FFTA_ROM:-${ROM_PATH:-}}}"

if [ -z "${ROM_PATH}" ]; then
    for cfg in "${REPO_ROOT}/config.toml" "${XDG_CONFIG_HOME:-$HOME/.config}/ffta-tool/config.toml"; do
        if [ -f "$cfg" ]; then
            val=$(grep -E '^\s*rom_file\s*=' "$cfg" | head -1 | cut -d'=' -f2 | tr -d ' "\047' || true)
            if [ -n "$val" ]; then
                eval "val=$val"
                if [ -f "$val" ]; then
                    ROM_PATH="$val"
                    break
                fi
            fi
        fi
    done
fi

if [ -z "${ROM_PATH}" ]; then
    for pattern in \
        "${REPO_ROOT}/*.gba" \
        "$HOME/Documents/FFTA_Assets/*.gba" \
        "$HOME/ROMs/GBA/*Final Fantasy Tactics Advance*.gba" \
        "$HOME/Roms/gba/*Final Fantasy Tactics Advance*.gba" \
        "$HOME/Emulation/roms/gba/*Final Fantasy Tactics Advance*.gba" \
        "$HOME/RetroPie/roms/gba/*Final Fantasy Tactics Advance*.gba" \
        "/run/media/*/*/Games/GBA/*Final Fantasy Tactics Advance*.gba"; do
        for match in $pattern; do
            if [ -f "$match" ]; then
                ROM_PATH="$match"
                break 2
            fi
        done
    done
fi

# Resolve SAV path: argument -> env -> config.toml -> repo default
SAV_PATH="${2:-${FFTA_SAV:-${SAV_PATH:-}}}"

if [ -z "${SAV_PATH}" ]; then
    for cfg in "${REPO_ROOT}/config.toml" "${XDG_CONFIG_HOME:-$HOME/.config}/ffta-tool/config.toml"; do
        if [ -f "$cfg" ]; then
            val=$(grep -E '^\s*save_file\s*=' "$cfg" | head -1 | cut -d'=' -f2 | tr -d ' "\047' || true)
            if [ -n "$val" ]; then
                eval "val=$val"
                if [ -f "$val" ]; then
                    SAV_PATH="$val"
                    break
                fi
            fi
        fi
    done
fi

if [ -z "${SAV_PATH}" ] || [ ! -f "${SAV_PATH}" ]; then
    SAV_PATH="${REPO_ROOT}/examples/FFTA_Super_Starter.sav"
fi

OUTPUT_DIR="${3:-${OUTPUT_DIR:-${SCRIPT_DIR}/output}}"

if [ -z "${ROM_PATH}" ] || [ ! -f "${ROM_PATH}" ]; then
    echo "Usage: $0 [path_to_ffta_rom.gba] [path_to_save.sav] [output_dir]"
    echo ""
    echo "ROM and Save Resolution:"
    echo "  1. CLI arguments: $0 <rom> <sav>"
    echo "  2. Environment variables: FFTA_ROM and FFTA_SAV"
    echo "  3. Configuration file: [paths] rom_file and save_file in config.toml"
    echo "  4. Automatic discovery across standard ROM and emulator directories"
    echo "  5. Default save fallback: examples/FFTA_Super_Starter.sav"
    echo ""
    echo "[!] Error: No FFTA GBA ROM found. Please specify ROM path or set FFTA_ROM / rom_file." >&2
    exit 1
fi

if [ ! -f "${SAV_PATH}" ]; then
    echo "[!] Error: Save file not found: ${SAV_PATH}" >&2
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# Select an available virtual display number between :99 and :130
DISPLAY_NUM=":99"
for d in {99..130}; do
    if [ ! -e "/tmp/.X11-unix/X$d" ] && [ ! -e "/tmp/.X$d-lock" ]; then
        DISPLAY_NUM=":$d"
        break
    fi
done

WORK_DIR="$(mktemp -d -t ffta_mgba_XXXXXX)"
XVFB_PID=""
MGBA_PID=""

cleanup() {
    set +e
    if [ -n "${MGBA_PID}" ] && kill -0 "${MGBA_PID}" 2>/dev/null; then
        kill -9 "${MGBA_PID}" 2>/dev/null || true
    fi
    if [ -n "${XVFB_PID}" ] && kill -0 "${XVFB_PID}" 2>/dev/null; then
        kill -9 "${XVFB_PID}" 2>/dev/null || true
    fi
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT INT TERM

echo "[*] Setting up headless environment on display ${DISPLAY_NUM}..."
"${XVFB}" "${DISPLAY_NUM}" -screen 0 800x600x24 -nolisten tcp > "${WORK_DIR}/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1

# Setup isolated sandbox files
cp "${ROM_PATH}" "${WORK_DIR}/game.gba"
cp "${SAV_PATH}" "${WORK_DIR}/game.sav"

echo "[*] Launching mGBA with ROM: $(basename "${ROM_PATH}") and SAV: $(basename "${SAV_PATH}")..."
DISPLAY="${DISPLAY_NUM}" \
SDL_AUDIODRIVER=dummy \
SDL_VIDEODRIVER=x11 \
"${MGBA}" -2 "${WORK_DIR}/game.gba" > "${WORK_DIR}/mgba.log" 2>&1 &
MGBA_PID=$!

export DISPLAY="${DISPLAY_NUM}"
WID=""
for i in {1..30}; do
    WID=$("${XDOTOOL}" search --onlyvisible --name "mGBA" 2>/dev/null | head -1 || true)
    if [ -n "${WID}" ]; then
        break
    fi
    sleep 1
done

if [ -z "${WID}" ]; then
    echo "[!] Error: mGBA failed to create a visible window within 30 seconds." >&2
    if [ -f "${WORK_DIR}/mgba.log" ]; then
        cat "${WORK_DIR}/mgba.log" >&2
    fi
    exit 1
fi

echo "[*] Found mGBA window (ID: ${WID}). Waiting 13s for boot logos and title screen..."
"${XDOTOOL}" windowfocus "${WID}"
sleep 13

echo "[*] Capturing Title screen..."
TITLE_FULL="${OUTPUT_DIR}/title_screen.png"
TITLE_CROP="${OUTPUT_DIR}/title_screen_crop.png"
"${IMPORT}" -window root "${TITLE_FULL}"
"${MAGICK}" "${TITLE_FULL}" -crop 480x320+160+140 "${TITLE_CROP}"

echo "[*] Sending Start button (Return) to open main menu..."
"${XDOTOOL}" windowfocus "${WID}"
for i in {1..3}; do
    "${XDOTOOL}" keydown Return
    sleep 0.4
    "${XDOTOOL}" keyup Return
    sleep 1
done
sleep 2

echo "[*] Selecting 'Load' option ('x' key / GBA A button)..."
"${XDOTOOL}" windowfocus "${WID}"
"${XDOTOOL}" keydown x
sleep 0.4
"${XDOTOOL}" keyup x
sleep 2

echo "[*] Capturing Save Slot Selection screen..."
SLOTS_FULL="${OUTPUT_DIR}/slots_screen.png"
SLOTS_CROP="${OUTPUT_DIR}/slots_screen_crop.png"
"${IMPORT}" -window root "${SLOTS_FULL}"
"${MAGICK}" "${SLOTS_FULL}" -crop 480x320+160+140 "${SLOTS_CROP}"

echo "[*] Selecting Slot 1 to load into world map..."
"${XDOTOOL}" windowfocus "${WID}"
"${XDOTOOL}" keydown x
sleep 0.4
"${XDOTOOL}" keyup x
sleep 5

echo "[*] Capturing World Map screen..."
MAP_FULL="${OUTPUT_DIR}/world_map.png"
MAP_CROP="${OUTPUT_DIR}/world_map_crop.png"
"${IMPORT}" -window root "${MAP_FULL}"
"${MAGICK}" "${MAP_FULL}" -crop 480x320+160+140 "${MAP_CROP}"

echo "[*] Opening Clan Unit Roster (Start button + 'x' button)..."
"${XDOTOOL}" windowfocus "${WID}"
"${XDOTOOL}" keydown Return
sleep 0.4
"${XDOTOOL}" keyup Return
sleep 2
"${XDOTOOL}" keydown x
sleep 0.4
"${XDOTOOL}" keyup x
sleep 2

echo "[*] Capturing Clan Unit Roster screen..."
ROSTER_FULL="${OUTPUT_DIR}/unit_roster.png"
ROSTER_CROP="${OUTPUT_DIR}/unit_roster_crop.png"
"${IMPORT}" -window root "${ROSTER_FULL}"
"${MAGICK}" "${ROSTER_FULL}" -crop 480x320+160+140 "${ROSTER_CROP}"

echo "[+] mGBA headless test completed successfully!"
echo "    Screenshots saved to: ${OUTPUT_DIR}/"
echo "      - ${TITLE_FULL} (and crop)"
echo "      - ${SLOTS_FULL} (and crop)"
echo "      - ${MAP_FULL} (and crop)"
echo "      - ${ROSTER_FULL} (and crop)"
