# main.py - Raspberry Pi Pico (MicroPython) orientation sensor for an external monitor.
#
# Reads an ADXL345 accelerometer over I2C, decides landscape vs portrait from the
# gravity vector, and prints the orientation over USB serial (one word per line)
# whenever it changes, and again every RESEND_S so a host that opens the port late
# still hears it. Hysteresis + debounce keep it from chattering near 45 deg or
# mid-rotation.
#
# Flash MicroPython to the Pico, then copy this file to the board as main.py so it
# runs on boot.
#
# Wiring (ADXL345 -> Pico, I2C0):
#   VCC -> 3V3 (pin 36)
#   GND -> GND
#   SDA -> GP0 (pin 1)
#   SCL -> GP1 (pin 2)
#   SDO -> GND  (sets I2C address to 0x53)
#
# Mount the breakout flat against the back of the panel so that, in LANDSCAPE,
# gravity points along the sensor's Y axis. If your mounting is rotated, adjust
# AXIS_MAIN / the decision in classify() below.

import math
import time

from machine import I2C, Pin

# Configuration
I2C_ID = 0
SDA_PIN = 0
SCL_PIN = 1
ADXL345_ADDR = 0x53

# Tilt thresholds (degrees from "panel upright"). Hysteresis band: only flip to
# portrait above ENTER, only flip back to landscape below EXIT. Keep EXIT < ENTER.
PORTRAIT_ENTER_DEG = 60.0
PORTRAIT_EXIT_DEG = 30.0

# Debounce: the candidate orientation must hold this long before we emit it.
DEBOUNCE_S = 0.6

# How often we sample the accelerometer.
SAMPLE_INTERVAL_S = 0.05

# Repeat the current orientation this often. Output is dropped while no host has
# the port open, so without this a daemon started after the Pico never hears it.
RESEND_S = 2.0

# ADXL345 registers
_REG_POWER_CTL = 0x2D
_REG_DATA_FORMAT = 0x31
_REG_DATAX0 = 0x32
_SCALE = 0.0039  # g/LSB in full-resolution mode


class ADXL345:
    def __init__(self, i2c, addr=ADXL345_ADDR):
        self.i2c = i2c
        self.addr = addr
        # Full resolution, +/-16g range.
        self.i2c.writeto_mem(self.addr, _REG_DATA_FORMAT, b"\x0b")
        # Exit standby -> measurement mode.
        self.i2c.writeto_mem(self.addr, _REG_POWER_CTL, b"\x08")

    def read(self):
        d = self.i2c.readfrom_mem(self.addr, _REG_DATAX0, 6)
        x = self._u2s(d[0] | (d[1] << 8))
        y = self._u2s(d[2] | (d[3] << 8))
        z = self._u2s(d[4] | (d[5] << 8))
        return (x * _SCALE, y * _SCALE, z * _SCALE)

    @staticmethod
    def _u2s(v):
        return v - 65536 if v & 0x8000 else v


def tilt_degrees(ax, ay):
    # Angle of the in-plane gravity vector away from the panel's Y axis.
    # 0 deg = upright/landscape, ~90 deg = turned to portrait.
    return abs(math.degrees(math.atan2(ax, ay)))


def main():
    i2c = I2C(I2C_ID, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=400_000)
    accel = ADXL345(i2c)

    # Smooth the angle a touch to reject single-sample noise.
    smoothed = None
    orientation = None  # last emitted orientation
    candidate = None  # orientation we're waiting to confirm
    candidate_since = 0
    sent_at = 0  # when the orientation was last printed

    while True:
        try:
            ax, ay, _ = accel.read()
        except OSError:
            time.sleep(0.2)
            continue

        deg = tilt_degrees(ax, ay)
        smoothed = deg if smoothed is None else (smoothed * 0.7 + deg * 0.3)

        # Hysteresis: choose the candidate orientation from the smoothed tilt.
        if smoothed >= PORTRAIT_ENTER_DEG:
            want = "portrait"
        elif smoothed <= PORTRAIT_EXIT_DEG:
            want = "landscape"
        else:
            want = orientation  # inside the dead band: hold current

        now = time.ticks_ms()
        if want != orientation:
            if want != candidate:
                candidate = want
                candidate_since = now
            elif time.ticks_diff(now, candidate_since) >= int(DEBOUNCE_S * 1000):
                orientation = candidate
                print(orientation)  # -> USB serial line
                sent_at = now
        else:
            candidate = orientation
            if orientation and time.ticks_diff(now, sent_at) >= int(RESEND_S * 1000):
                print(orientation)
                sent_at = now

        time.sleep(SAMPLE_INTERVAL_S)


if __name__ == "__main__":
    main()
