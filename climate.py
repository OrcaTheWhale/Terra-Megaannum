"""
climate.py - seasons and temperature.

The model doesn't forecast weather. It takes a climate input (the yearly average
and seasonal swing in config.py, later adjusted by the sensor) and works out:
  - the sea-level temperature for any part of the year
  - the temperature at every point on the map, from its height (lapse rate)
"""

import math

import numpy as np

from config import AVG_TEMP_C, SEASON_SWING_C, WARMEST_DAY, MIN_ELEVATION_M, MAX_ELEVATION_M

LAPSE_RATE = 6.5 / 1000      # air gets about 6.5 C colder per 1000 m higher
YEAR = 365

# Extra degrees on top of the normal climate: set by main.py from the
# temperature sensor (and the Up/Down keys). +2 means "2 C warmer than normal".
warming_c = 0.0


def sea_level_temp(start_day, length_days):
    """Average sea-level temperature over a stretch of time.

    Temperature follows a wave over the year:
        T(t) = AVG + SWING * cos(2*pi*(t - WARMEST_DAY) / 365)
    We average that wave over the step, so a 1-day step gets that day's temperature,
    a season step gets that season's average, and a whole year averages out to AVG.
    """
    w = 2 * math.pi / YEAR
    a = start_day - WARMEST_DAY
    b = a + length_days
    # average of cos over [a, b] = (sin(w*b) - sin(w*a)) / (w * (b - a))
    wave_average = (math.sin(w * b) - math.sin(w * a)) / (w * length_days)
    return AVG_TEMP_C + warming_c + SEASON_SWING_C * wave_average


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
    return MIN_ELEVATION_M + heights / 255 * (MAX_ELEVATION_M - MIN_ELEVATION_M)


def temperature_map(heights, sea_temp):
    """Temperature (C) at every point: colder the higher you go."""
    return sea_temp - LAPSE_RATE * elevation_m(heights)


def freezing_fraction(heights, sea_temp):
    """Share of the map that's below 0 C (0 to 1)."""
    return float(np.mean(temperature_map(heights, sea_temp) < 0))