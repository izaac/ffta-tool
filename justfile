# Final Fantasy Tactics Advance (FFTA) Tool - Justfile

default:
    @just --list

# Install ffta-tool in editable mode (supports uv or standard pip)
install:
    @if command -v uv >/dev/null 2>&1; then \
        uv pip install -e . ; \
    else \
        python3 -m pip install -e . ; \
    fi

# Run comprehensive test suite
test:
    python3 -m unittest discover tests

md_targets := "docs/*.md README.md support/README.md"
md_ignores := "MD013,MD024,MD026,MD033,MD036,MD041"

# Lint and check codebase
check: test pycheck (mdlint "scan")

# Format codebase
fmt: pyfmt (mdlint "fix")

[private]
mdlint action:
    @if command -v uvx >/dev/null 2>&1; then \
        uvx pymarkdownlnt -d {{md_ignores}} {{action}} {{md_targets}} ; \
    elif command -v pymarkdownlnt >/dev/null 2>&1; then \
        pymarkdownlnt -d {{md_ignores}} {{action}} {{md_targets}} ; \
    elif python3 -m pymarkdownlnt --version >/dev/null 2>&1; then \
        python3 -m pymarkdownlnt -d {{md_ignores}} {{action}} {{md_targets}} ; \
    fi

[private]
pycheck:
    @if command -v uvx >/dev/null 2>&1; then \
        uvx ruff check . ; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff check . ; \
    else \
        python3 -m ruff check . ; \
    fi

[private]
pyfmt:
    @if command -v uvx >/dev/null 2>&1; then \
        uvx ruff format . && uvx ruff check --fix . ; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff format . && ruff check --fix . ; \
    else \
        python3 -m ruff format . && python3 -m ruff check --fix . ; \
    fi

# Sync ROMs and saves to Analogue Pocket SD card
sync:
    python3 support/sync_pocket.py

# Validate all local and Pocket saves
validate:
    python3 support/validate_saves.py

# Non-destructive clan top-up (preserves high speed, equips meta builds)
topup:
    python3 support/topup_clan_units.py --sync

# Regenerate all 5 canonical race fleet saves and sync to Pocket
fleets:
    python3 support/generate_race_save.py all --sync
