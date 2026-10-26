# monitor-autorotate

Turn an external monitor in **aion** when it is rotated on its VESA arm. A Pico with an
accelerometer on the back of the panel reports `portrait` or `landscape`, and a user
service hands that to `aion msg profile`, which moves every monitor to its rule in that
profile. You don't have to do anything when you turn the monitor.

Built for: [aion](https://github.com/boatette/aion), external monitor `HDMI-A-1` on
aspire, and the NixOS config in `~/nix`.

## Bill of materials (~$15)

| Part                           | Approx. | Notes                                                                      |
| ------------------------------ | ------- | -------------------------------------------------------------------------- |
| Raspberry Pi Pico (RP2040)     | $4–5    | Runs MicroPython, shows up as USB serial. "Pico H" = pre-soldered headers. |
| ADXL345 accelerometer breakout | $3–6    | 3-axis accelerometer, I2C. MPU-6050 (~$3) also works; we ignore its gyro.  |
| Female–female jumper wires     | $2      | 4 needed.                                                                  |
| Micro-USB cable (long)         | $3      | Leave slack/strain-relief so it survives the arm rotating.                 |
| Adhesive pad / bracket         | —       | Fix the sensor flat to the back of the panel.                              |

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
                   ▼  prints it over USB serial on every change, and every 2 s
 /dev/monitor-orient   udev symlink, usable by whoever is logged in at the seat
                   │
 monitor-autorotate    daemon/monitor-autorotate.sh, a user service in aion-session.target
                   ▼  aion msg profile portrait|landscape, once per change
 aion                  moves every monitor to its rule in that profile (transform + position)
```

aion's monitor rules are compiled into its config, one set per profile. Nothing is
stored on disk. aion starts in the first profile by name (`landscape`), and the Pico's
next line, at most 2 s later, corrects it. The repeat also means a daemon that starts
after the Pico, at login or after a replug, still finds out the current orientation.

## NixOS

The flake has a `nixosModules.default` that needs `programs.aion`:

```nix
{
  inputs.monitor-autorotate = {
    url = "git+file:///home/boatette/Projects/monitor-autorotate";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  # in a NixOS module
  imports = [ inputs.monitor-autorotate.nixosModules.default ];
  services.monitor-autorotate.enable = true;
}
```

It adds:

- A udev rule (ordered before `73-seat-late.rules`, so `uaccess` works) that gives a Pico
  running MicroPython (`2e8a:0005`) the symlink `/dev/monitor-orient`, readable by
  whoever is logged in.
- `monitor-autorotate.service`, a user service that runs while aion does. It waits for
  the sensor when the sensor is unplugged.

aion's config needs rules for both profiles, e.g.:

```zig
pub const monrules = [_]a.MonitorRule{
    .{ .name = "HDMI-A-1", .profile = "landscape", .x = 0, .y = 0 },
    .{ .name = "eDP-1", .profile = "landscape", .x = 1920, .y = 0 },
    .{ .name = "HDMI-A-1", .profile = "portrait", .transform = .@"90", .x = 0, .y = 0 },
    .{ .name = "eDP-1", .profile = "portrait", .x = 1080, .y = 420 },
    .{},
};
```

In `~/nix`, `modules/programs/aion.nix` generates these from `profiles` in
`flake.monitors` (`modules/hosts/aspire/monitors.nix`), and
`modules/services/monitor-autorotate.nix` enables the service on aspire.

## Firmware

`nix develop` has `mpremote`.

1. Hold BOOTSEL, plug in the Pico, drop the MicroPython `.uf2` onto the `RPI-RP2`
   drive (from micropython.org/download/RPI_PICO).
2. Copy `firmware/main.py` to the board as `main.py`. It runs on boot:
   `mpremote cp firmware/main.py :main.py`

## Testing

**No hardware needed.** Switch aion's profile by hand:

```sh
aion msg profile portrait
aion msg profile landscape
aion msg profile                  # prints the active one
aion msg monitors                 # HDMI-A-1 is 1080 wide in portrait, 1920 in landscape
```

**With the Pico.** Stop the service first, so the two readers don't split the lines:

```sh
ls -l /dev/monitor-orient
systemctl --user stop monitor-autorotate
stty -F /dev/monitor-orient raw -echo && cat /dev/monitor-orient   # tilt by hand, watch the words
systemctl --user start monitor-autorotate
journalctl --user -u monitor-autorotate -f                         # "turning to portrait"
```

## Tuning

In `firmware/main.py`:

- `PORTRAIT_ENTER_DEG` / `PORTRAIT_EXIT_DEG`: the hysteresis band (avoids flicker near 45°).
- `DEBOUNCE_S`: how long an orientation must hold before it's emitted (rejects mid-turn wobble).
- `RESEND_S`: how often the current orientation is repeated.

Each profile's transform and position live in the aion config (`flake.monitors` in `~/nix`).

## Notes / limitations

- The USB cable rotates with the arm, so leave a service loop.
- aion has a single scrolling layout, so nothing changes per orientation apart from the
  monitor itself. Column widths are fractions of the monitor, so columns get narrower
  or wider as it turns.
- A turn while the monitors are off (idle) is applied when they wake. Turning also works
  while the session is locked.
- The udev rule matches any Pico running MicroPython. With a second one plugged in,
  `/dev/monitor-orient` may point at the wrong board.
