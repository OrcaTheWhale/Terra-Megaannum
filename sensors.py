"""sensors.py - reads the ESP32's sensor lines in the background.
Line format: S,millis,temp,humidity,light,flame,tilt,direction
Test on its own: python sensors.py
"""

import math
import threading
import time

import serial
import serial.tools.list_ports

# what each comma-separated column means
COLUMNS = ['tag', 'ms', 'temp', 'hum', 'light', 'flame', 'tilt', 'dir']

# raw value that means 0, raw value that means 1. Bigger number first flips it.
# Measure these on the day and adjust.
CALIBRATION = {
    'light': (4095, 0),    # our photoresistor reads LOWER in bright light
    'tilt':  (0, 30),      # joystick centred -> pushed all the way (the ESP32 sends 0-30)
}

# ZERO POINT: when the simulation starts (and with the Z key) every sensor's reading is saved
# as its zero point, and the app reacts to CHANGES from it. So the room's own temperature,
# humidity and light don't matter, and the flame sensor works whichever way it's wired.
HUM_PER_EXTRA_RAIN = 3.0   # % humidity above the zero point that adds 1x the menu's rain
                           # (breathe on it: +4% -> 2x rain, +7% -> 3x). Lower = more sensitive.
HUM_DEADBAND = 1.0         # ignore changes this small (the DHT11 only reads whole %)
LIGHT_GAIN = 2.0           # sunlight multiplier change per 1.0 of light change (0-1 scale)
FIRE_RISE = 0.3            # flame reading must move this share of the way to its far end to be "fire"

SMOOTHING = 0.2            # 0..1: lower = smoother but slower to react
BAUD = 115200
STALE_AFTER = 2.0          # seconds without data counts as disconnected


def find_port():
    hints = ('CP210', 'CH340', 'CH910', 'USB', 'UART', 'SLAB', 'ttyACM')
    for p in serial.tools.list_ports.comports():
        if any(h.lower() in (p.description + p.device).lower() for h in hints):
            return p.device
    return None


def parse_line(line):
    """'S,15320,22.0,...' -> {'ms': 15320.0, 'temp': 22.0, ...}, or None if it isn't a sensor line."""
    parts = line.strip().split(',')
    if len(parts) != len(COLUMNS) or parts[0] != 'S':
        return None
    try:
        return {name: float(value) for name, value in zip(COLUMNS[1:], parts[1:])}
    except ValueError:
        return None


class SensorReader:
    def __init__(self, port=None):
        self.port = port
        self.values = {}             # smoothed latest values
        self.last_time = 0.0
        self.lines = 0
        self.error = ''
        self.base = {}               # zero point of each sensor (see ZERO POINT above)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    # ------------------------------------------------------------ reading values
    def connected(self):
        return time.time() - self.last_time < STALE_AFTER

    def has(self, name):
        return self.connected() and name in self.values

    def get(self, name, default=0.0):
        return self.values.get(name, default)

    def norm(self, name, default=0.0):
        """Value scaled to 0..1 using CALIBRATION."""
        if name not in self.values:
            return default
        lo, hi = CALIBRATION.get(name, (0, 4095))
        return min(1.0, max(0.0, (self.values[name] - lo) / (hi - lo)))

    def change(self, name):
        """How far a sensor has moved from its zero point (0 until it has a reading).
        The first reading becomes the zero point if rezero() hasn't set one yet."""
        if name not in self.values:
            return 0.0
        base = self.base.setdefault(name, self.values[name])
        return self.values[name] - base

    def temp_change(self):
        """How many degrees warmer (+) or colder (-) than at the zero point."""
        return self.change('temp')

    def rain_factor(self):
        """Humidity change -> rain multiplier: 1 at the zero point, up to 3x breathed on,
        down to 0.25x in drier air."""
        d = self.change('hum')
        d = math.copysign(max(0.0, abs(d) - HUM_DEADBAND), d)
        return min(3.0, max(0.25, 1 + d / HUM_PER_EXTRA_RAIN))

    def sunlight(self):
        """Light change -> how fast plants grow: 1 at the zero point, 0.3 (covered) to 1.7 (torch)."""
        if 'light' not in self.values:
            return 1.0
        lo, hi = CALIBRATION['light']
        base = (self.base.setdefault('light', self.values['light']) - lo) / (hi - lo)
        return min(1.7, max(0.3, 1 + LIGHT_GAIN * (self.norm('light') - base)))

    def fire_level(self):
        """0-1: how far the flame reading has moved from its zero point toward its far end."""
        if 'flame' not in self.values:
            return 0.0
        base = self.base.setdefault('flame', self.values['flame'])
        now = self.values['flame']
        if base >= 2048:
            level = (base - now) / max(base, 1)              # reads lower near a flame
        else:
            level = (now - base) / max(4095 - base, 1)       # reads higher near a flame
        return min(1.0, max(0.0, level))

    def rezero(self):
        """Save every sensor's current reading as its zero point (simulation start, or Z)."""
        self.base = dict(self.values)

    def wind(self):
        """(strength 0..1, direction in degrees or None)."""
        strength = self.norm('tilt')
        direction = self.values.get('dir', -1)
        return strength, (None if direction < 0 else direction)

    # ------------------------------------------------------------ background thread
    def _run(self):
        port = self.port or find_port()
        if port is None:
            self.error = 'no ESP32 found'
            return
        try:
            ser = serial.Serial(port, BAUD, timeout=1)
            self.port = port
        except serial.SerialException:
            self.error = f"couldn't open {port} (is the serial monitor open?)"
            return

        while True:
            try:
                line = ser.readline().decode(errors='ignore')
            except serial.SerialException:
                self.error = 'ESP32 unplugged'
                return
            reading = parse_line(line)
            if reading is None:
                continue
            for name, value in reading.items():
                if math.isnan(value):
                    continue                      # e.g. DHT11 not read yet
                if name in ('ms', 'dir') or name not in self.values:
                    self.values[name] = value     # no smoothing for time or direction
                else:
                    old = self.values[name]
                    self.values[name] = old + SMOOTHING * (value - old)
            self.lines += 1
            self.last_time = time.time()
            self.error = ''


# ---------------------------------------------------------------- self-test
if __name__ == '__main__':
    import sys
    reader = SensorReader(sys.argv[1] if len(sys.argv) > 1 else None)
    reader.start()
    print('Reading sensors... (Ctrl+C to stop)')
    while True:
        time.sleep(0.5)
        if not reader.connected():
            print('waiting for ESP32...', reader.error)
            continue
        strength, direction = reader.wind()
        print(f"temp {reader.get('temp'):5.1f} C ({reader.temp_change():+.1f})  "
              f"hum {reader.get('hum'):4.0f}% ({reader.change('hum'):+.1f}, rain x{reader.rain_factor():.2f})  "
              f"light raw {reader.get('light'):4.0f} (sun x{reader.sunlight():.2f})  "
              f"flame raw {reader.get('flame'):4.0f} (fire {reader.fire_level():.2f})  "
              f"wind {strength:.2f} toward {direction if direction is not None else '-'}")
