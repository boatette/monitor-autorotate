#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HYPR="$HOME/.config/hypr"
SCRIPTS="$HYPR/scripts"
STATE="$HYPR/state/orientation"

echo "==> monitor-autorotate install"

# 1) Dependency
if ! python3 -c "import serial" 2>/dev/null; then
    echo "--> pyserial is missing. Install it with:"
    echo "      sudo pacman -S python-pyserial"
else
    echo "--> pyserial present."
fi

# 2) Daemon
mkdir -p "$SCRIPTS"
install -m 0755 "$SRC/daemon/orientation-daemon.py" "$SCRIPTS/orientation-daemon.py"
echo "--> installed $SCRIPTS/orientation-daemon.py"

# 3) State file (don't clobber an existing one)
mkdir -p "$(dirname "$STATE")"
if [[ -f "$STATE" ]]; then
    echo "--> state file already exists: $STATE ($(cat "$STATE"))"
else
    cp "$SRC/hypr/orientation.state" "$STATE"
    echo "--> seeded $STATE (landscape)"
fi

# 4) Config edits -- shown, not auto-applied
cat <<EOF

==> Two manual config edits remain (one-time):

  1. cfg/output.lua  -- replace the hard-coded orientation toggle with the
     state-file reader. See:
       $SRC/hypr/output.lua.snippet

  2. cfg/exec.lua    -- add the daemon to the hyprland.start block:
       $SRC/hypr/exec.lua.snippet

  Then reload:  hyprctl reload

==> Test it now WITHOUT the sensor:
       python3 $SCRIPTS/orientation-daemon.py --apply portrait
       python3 $SCRIPTS/orientation-daemon.py --apply landscape

  (Each writes the state file, rotates HDMI-A-1 live, and reloads.)

==> Firmware: flash MicroPython to the Pico, then copy
       $SRC/firmware/main.py  ->  the board as main.py
EOF

echo "==> done."
