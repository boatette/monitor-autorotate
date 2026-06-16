# monitor-autorotate

Auto-rotate an external monitor in **Hyprland** from a physical orientation sensor
mounted on the panel. When the monitor is turned on its rotating VESA arm, a tiny
accelerometer tells a host daemon to rotate the display and switch workspaces 11-18
between the `scrolling` and `lua:gridscroll` layouts — no manual step.

Built for: Hyprland 0.55.4, external monitor `HDMI-A-1`, the Hyprland-in-Lua config
under `~/.config/hypr`.

## Why an accelerometer (not a gyroscope)

A gyroscope measures angular *velocity* — it knows you're rotating but drifts and
can't read a resting orientation. An **accelerometer** at rest measures the gravity
vector, which directly tells landscape from portrait. (IMU chips usually bundle both;
we only use the accelerometer.)

## Bill of materials (~$15)

| Part | Approx. | Notes |
|------|---------|-------|
| Raspberry Pi Pico (RP2040) | $4–5 | Runs MicroPython, shows up as USB serial. "Pico H" = pre-soldered headers. |
| ADXL345 accelerometer breakout | $3–6 | 3-axis accelerometer, I2C. MPU-6050 (~$3) also works; we ignore its gyro. |
| Female–female jumper wires | $2 | 4 needed. |
| Micro-USB cable (long) | $3 | Leave slack/strain-relief so it survives the arm rotating. |
| Adhesive pad / bracket | — | Fix the sensor flat to the back of the panel. |

## Wiring (ADXL345 → Pico, I2C0)

```
ADXL345        Pico
  VCC  ──────  3V3  (pin 36)
  GND  ──────  GND
  SDA  ──────  GP0  (pin 1)
  SCL  ──────  GP1  (pin 2)
  SDO  ──────  GND   (I2C address 0x53)
```

Mount the breakout flat against the panel back so that, in **landscape**, gravity
points along the sensor's **Y** axis. If your mounting is rotated, tweak
`tilt_degrees()` in `firmware/main.py`.

## How it works

```
 ADXL345 ──I2C──▶ Pico (firmware/main.py)
                   │  decides portrait/landscape (hysteresis + debounce)
                   ▼  prints "portrait"/"landscape" over USB serial on change
 host: daemon/orientation-daemon.py
                   │  writes ~/.config/hypr/state/orientation
                   │  rotates HDMI-A-1 live (hyprctl keyword monitor ...)
                   ▼  hyprctl reload
 Hyprland: cfg/output.lua reads the state file → monitor transform 1/0
           cfg/workspaces.lua → workspaces 11-18 = gridscroll / scrolling
```

`hyprctl reload` re-runs `output.lua` (rotation) and `workspaces.lua` (layout) in one
shot. It does **not** re-run `exec.lua` autostart, so the daemon never respawns itself.
The 11-18 layout switch is resolved at config-parse time, which is why a reload (not a
bare keyword) is used to apply it.

## Files

```
firmware/main.py                 MicroPython for the Pico + ADXL345
daemon/orientation-daemon.py     host daemon (serial → Hyprland)
hypr/output.lua.snippet          edit for cfg/output.lua (read orientation from state file)
hypr/exec.lua.snippet            edit for cfg/exec.lua (autostart the daemon)
hypr/orientation.state           seed for ~/.config/hypr/state/orientation
udev/99-monitor-orient.rules     optional stable /dev symlink
systemd/monitor-autorotate.service  optional alternative to exec.lua autostart
install.sh                       copies daemon + state file, prints the config edits
```

## Install

```sh
./install.sh                       # copies daemon + seeds state, prints next steps
sudo pacman -S python-pyserial     # if not already present
```

Then apply the two config edits shown by the installer (`hypr/output.lua.snippet`
and `hypr/exec.lua.snippet`) and `hyprctl reload`.

### Firmware

1. Hold BOOTSEL, plug in the Pico, drop the MicroPython `.uf2` onto the `RPI-RP2`
   drive (from micropython.org/download/RPI_PICO).
2. Copy `firmware/main.py` to the board as `main.py` (e.g. with `mpremote`:
   `mpremote cp firmware/main.py :main.py`). It runs on boot.

## Testing

**No hardware needed** — drive it by hand to prove the Hyprland side:

```sh
python3 ~/.config/hypr/scripts/orientation-daemon.py --apply portrait
python3 ~/.config/hypr/scripts/orientation-daemon.py --apply landscape
hyprctl monitors -j | jq '.[] | select(.name=="HDMI-A-1") | .transform'   # 1 vs 0
```

**Simulate the serial stream:**

```sh
printf 'portrait\nlandscape\n' | \
  python3 ~/.config/hypr/scripts/orientation-daemon.py --simulate
```

**With the Pico:**

```sh
ls /dev/serial/by-id/                 # confirm it enumerates
cat /dev/serial/by-id/usb-MicroPython*-if00   # tilt by hand, watch the words
```

Then mount on the arm, start the daemon (or relog), and physically rotate.

## Tuning

In `firmware/main.py`:
- `PORTRAIT_ENTER_DEG` / `PORTRAIT_EXIT_DEG` — the hysteresis band (avoid flicker near 45°).
- `DEBOUNCE_S` — how long an orientation must hold before it's emitted (rejects mid-turn wobble).

In `daemon/orientation-daemon.py`:
- `GEOMETRY` — transform/position per orientation (must match `cfg/output.lua`).
- `--no-reload` — rotate live only, skip the layout switch.

## Notes / limitations

- The USB cable rotates with the arm — leave a service loop.
- A physical rotation triggers a full `hyprctl reload` (brief, fine for occasional turns).
- Windows already open on workspaces 11-18 may not perfectly re-tile when the layout
  flips on reload; newly opened windows always use the new layout.
