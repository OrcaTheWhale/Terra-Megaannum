"""
sensors.py - reads the ESP32's sensor lines in the background.

The ESP32 sends lines like:   S,15320,22.0,45.0,1874,4095,3.2,135
COLUMNS says what each position means (it must match the ESP32's printf).

Usage:
    sensors = SensorReader()        # or SensorReader('COM5')
    sensors.start()
    sensors.get('hum')              # smoothed raw value, e.g. 45.0
    sensors.norm('light')           # scaled 0..1 using CALIBRATION
    sensors.temp_change()           # degrees C warmer (+) or colder (-) than at startup

Test it on its own (ESP32 plugged in, serial monitor closed):
    python sensors.py
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
    'flame': (4095, 0),    # flame sensor reads lower near a flame / IR remote
    'hum':   (40, 90),     # room air -> breathed on
    'tilt':  (0, 30),      # hanging still -> blown hard (degrees)
}

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
        self.start_temp = None       # temperature when the app started (for temp_change)

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

    def temp_change(self):
        """How many degrees warmer (+) or colder (-) than when the app started."""
        if self.start_temp is None or 'temp' not in self.values:
            return 0.0
        return self.values['temp'] - self.start_temp

    def rezero(self):
        """Treat the current temperature as 'no change' again."""
        if 'temp' in self.values:
            self.start_temp = self.values['temp']

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
            if self.start_temp is None and 'temp' in self.values:
                self.start_temp = self.values['temp']
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
        print(f"temp {reader.get('temp'):5.1f} C (change {reader.temp_change():+.1f})  "
              f"hum {reader.get('hum'):4.0f}% (rain {reader.norm('hum'):.2f})  "
              f"light {reader.norm('light'):.2f}  flame {reader.norm('flame'):.2f}  "
              f"wind {strength:.2f} toward {direction if direction is not None else '-'}")



#average temp: 25.3C
#average hum: 14-15%, percentage after breath: 25%
#light: 0.0-0.1, tune for 0.50-1
#flame normal: 0.90
#gy-521: 0-360