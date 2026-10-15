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

# Lint and check codebase
check: test
    @if command -v uvx >/dev/null 2>&1; then \
        uvx ruff check . ; \
        uvx pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 scan docs/*.md README.md support/README.md ; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff check . ; \
        if command -v pymarkdownlnt >/dev/null 2>&1; then \
            pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 scan docs/*.md README.md support/README.md ; \
        fi ; \
    else \
        python3 -m ruff check . ; \
        if python3 -m pymarkdownlnt --version >/dev/null 2>&1; then \
            python3 -m pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 scan docs/*.md README.md support/README.md ; \
        fi ; \
    fi

# Format codebase
fmt:
    @if command -v uvx >/dev/null 2>&1; then \
        uvx ruff format . && uvx ruff check --fix . ; \
        uvx pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 fix docs/*.md README.md support/README.md ; \
    elif command -v ruff >/dev/null 2>&1; then \
        ruff format . && ruff check --fix . ; \
        if command -v pymarkdownlnt >/dev/null 2>&1; then \
            pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 fix docs/*.md README.md support/README.md ; \
        fi ; \
    else \
        python3 -m ruff format . && python3 -m ruff check --fix . ; \
        if python3 -m pymarkdownlnt --version >/dev/null 2>&1; then \
            python3 -m pymarkdownlnt -d MD013,MD024,MD026,MD033,MD036,MD041 fix docs/*.md README.md support/README.md ; \
        fi ; \
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
