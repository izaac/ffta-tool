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
    @if command -v npx >/dev/null 2>&1; then \
        npx markdownlint-cli "docs/*.md" "README.md" "support/README.md" ; \
    fi

# Format markdown documentation
fmt:
    @if command -v npx >/dev/null 2>&1; then \
        npx markdownlint-cli --fix "docs/*.md" "README.md" "support/README.md" ; \
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
