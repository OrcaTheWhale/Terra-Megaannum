"""climate.py - temperature: seasons over the year, colder higher up (6.5 C per km),
the snow line, lake evaporation and how much rain runs off.
"""

import math

import numpy as np

import config      # read as config.AVG_TEMP_C etc., so values typed in the menu are used

LAPSE_RATE = 6.5 / 1000      # air gets about 6.5 C colder per 1000 m higher
YEAR = 365

# Extra degrees on top of the normal climate: set by main.py from the
# temperature sensor (and the Up/Down keys). +2 means "2 C warmer than normal".
warming_c = 0.0

# Yearly rain (mm) right now: set by main.py from the menu, humidity sensor and [ ] keys.
# None = use ANNUAL_RAIN_MM from config.py.
rain_mm = None


# Sunlight compared with normal (1 = normal): set by main.py from the light sensor.
sunlight = 1.0

# Wind: strength 0-1 and the direction it blows toward (degrees). Set by main.py from the
# joystick, or from config.py / the J K Y keys when the sensor isn't connected.
wind_strength = 0.0
wind_toward = 0.0


def current_rain_mm():
    return config.ANNUAL_RAIN_MM if rain_mm is None else rain_mm


def sea_level_temp(start_day, length_days):
    """Average sea-level temperature over a stretch of time."""
    w = 2 * math.pi / YEAR
    a = start_day - config.WARMEST_DAY
    b = a + length_days
    # average of cos over [a, b] = (sin(w*b) - sin(w*a)) / (w * (b - a))
    wave_average = (math.sin(w * b) - math.sin(w * a)) / (w * length_days)
    return config.AVG_TEMP_C + warming_c + config.SEASON_SWING_C * wave_average


def season_name(day_of_year):
    """Northern hemisphere seasons."""
    d = day_of_year % YEAR
    if d < 59 or d >= 334:
        return 'Winter'
    if d < 151:
        return 'Spring'
    if d < 243:
        return 'Summer'
    return 'Autumn'


def elevation_m(heights):
    """Heights on the 0-255 scale -> real metres."""
    low, high = config.MIN_ELEVATION_M, config.MAX_ELEVATION_M
    return low + heights / 255 * (high - low)


def temperature_map(heights, sea_temp):
    """Temperature (C) at every point: colder the higher you go."""
    return sea_temp - LAPSE_RATE * elevation_m(heights)


def snow_line(sea_temp):
    """Height where it's 0 C, on the map's 0-1 scale (0 = lowest point, 1 = highest)."""
    freezing_m = sea_temp / LAPSE_RATE
    low, high = config.MIN_ELEVATION_M, config.MAX_ELEVATION_M
    return (freezing_m - low) / (high - low)


def lake_evaporation_mm(temp_c):
    """How much water evaporates from a lake surface in a year (mm), at a yearly mean temperature."""
    return 700 * 1.07 ** (temp_c - 8)


def runoff_mm(rain_mm, evaporation_mm, w=2.6):
    """How much of the yearly rain runs off the land into rivers and lakes (mm/yr)."""
    rain = np.maximum(np.asarray(rain_mm, dtype=float), 1e-9)   # works for one number or a map
    aridity = evaporation_mm / rain
    evaporated_share = 1 + aridity - (1 + aridity ** w) ** (1 / w)
    runoff = np.where(np.asarray(rain_mm) > 0, rain * (1 - evaporated_share), 0.0)
    return float(runoff) if runoff.ndim == 0 else runoff


def freezing_fraction(heights, sea_temp):
    """Share of the map that's below 0 C (0 to 1)."""
    return float(np.mean(temperature_map(heights, sea_temp) < 0))
