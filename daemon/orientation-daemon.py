#!/usr/bin/env python3
"""Monitor auto-rotate daemon.

Reads orientation lines (`portrait` / `landscape`) from the Pico sensor over USB
serial and rotates the external monitor in Hyprland to match. The orientation is
written to a small state file that `cfg/output.lua` reads, then `hyprctl reload`
applies both the monitor rotation and the workspaces 11-18 layout switch
(scrolling <-> lua:gridscroll) in one shot.

Usage:
  orientation-daemon.py                 # run the serial loop (normal mode)
  orientation-daemon.py --apply portrait    # one-shot: set orientation now (no hardware)
  orientation-daemon.py --apply landscape
  orientation-daemon.py --simulate          # read orientation words from stdin (testing)
  orientation-daemon.py --no-reload         # only rotate live via keyword, skip reload

The serial device is found by its stable by-id path so it survives re-plugging.
"""

import argparse
import glob
import os
import subprocess
import sys
import time

# Configuration
MONITOR = "HDMI-A-1"
MODE = "1920x1080@75"
SCALE = "1"

# Per-orientation monitor geometry. Must match hyprland config
GEOMETRY = {
    "portrait": {"transform": 1, "position": "-1080x-420"},
    "landscape": {"transform": 0, "position": "-1920x0"},
}

STATE_FILE = os.path.expanduser("~/.config/hypr/state/orientation")

# Glob for the Pico's USB CDC by-id path
SERIAL_GLOB = "/dev/serial/by-id/usb-MicroPython*-if00"
SERIAL_BAUD = 115200

VALID = ("portrait", "landscape")


def log(*a):
    print("[autorotate]", *a, file=sys.stderr, flush=True)


def hyprctl(*args):
    return subprocess.run(["hyprctl", *args], capture_output=True, text=True)


def live_rotate(orientation):
    """Rotate the monitor immediately (no reload) for snappy feedback."""
    g = GEOMETRY[orientation]
    spec = f"{MONITOR},{MODE},{g['position']},{SCALE},transform,{g['transform']}"
    hyprctl("keyword", "monitor", spec)


def write_state(orientation):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(orientation + "\n")
    os.replace(tmp, STATE_FILE)


def read_state():
    try:
        with open(STATE_FILE) as f:
            v = f.read().strip()
            return v if v in VALID else None
    except OSError:
        return None


def apply(orientation, do_reload=True):
    """Set orientation: persist state, rotate live, then reload to sync layout."""
    if orientation not in VALID:
        log("ignoring invalid orientation:", orientation)
        return
    if read_state() == orientation:
        return
    log("-> switching to", orientation)
    write_state(orientation)
    live_rotate(orientation)
    if do_reload:
        hyprctl("reload")


def find_serial():
    matches = sorted(glob.glob(SERIAL_GLOB))
    return matches[0] if matches else None


def serial_loop(do_reload=True):
    try:
        import serial
    except ImportError:
        log("pyserial not installed. Install with: sudo pacman -S python-pyserial")
        sys.exit(1)

    while True:
        port = find_serial()
        if not port:
            log("waiting for sensor at", SERIAL_GLOB)
            time.sleep(2)
            continue
        try:
            log("connected:", port)
            with serial.Serial(port, SERIAL_BAUD, timeout=2) as ser:
                for raw in ser:
                    word = raw.decode("utf-8", "replace").strip().lower()
                    if word in VALID:
                        apply(word, do_reload=do_reload)
        except (serial.SerialException, OSError) as e:
            log("serial dropped:", e, "- reconnecting")
            time.sleep(2)


def stdin_loop(do_reload=True):
    log("simulate mode: type 'portrait' or 'landscape' + Enter (Ctrl-D to quit)")
    for line in sys.stdin:
        word = line.strip().lower()
        if word in VALID:
            apply(word, do_reload=do_reload)
        elif word:
            log("ignored:", word)


def main():
    ap = argparse.ArgumentParser(description="Monitor auto-rotate daemon")
    ap.add_argument("--apply", choices=VALID, help="set orientation once and exit")
    ap.add_argument("--simulate", action="store_true", help="read words from stdin")
    ap.add_argument(
        "--no-reload",
        action="store_true",
        help="rotate live only; skip hyprctl reload (no layout switch)",
    )
    args = ap.parse_args()
    do_reload = not args.no_reload

    if args.apply:
        apply(args.apply, do_reload=do_reload)
    elif args.simulate:
        stdin_loop(do_reload=do_reload)
    else:
        serial_loop(do_reload=do_reload)


if __name__ == "__main__":
    main()
