"""rain.py - wind-driven rain: wind pushes air up the slopes it hits, so they get more rain
and the far side gets a rain shadow. Extra rain ~ wind speed x uphill slope;
the average stays the menu's yearly rain.
"""

import numpy as np
from scipy.ndimage import gaussian_filter

import climate

SMOOTH_M = 600       # clouds react to the terrain smoothed over about this distance
MIN_SHARE = 0.15     # even the driest rain shadow keeps this share of the average rain


def wind_speed_ms(strength):
    """Wind strength 0-1 (joystick) -> wind speed in m/s (calm breeze to a strong 20 m/s)."""
    return 2 + 18 * strength


def rain_map(h, cell_m, average_rain_mm, strength, toward_deg):
    """Yearly rain (mm) at every point. strength 0-1, toward_deg = direction the wind blows TO."""
    if strength < 0.05 or average_rain_mm <= 0:
        return np.full(h.shape, float(average_rain_mm))
    z = gaussian_filter(climate.elevation_m(np.asarray(h, dtype=float)), SMOOTH_M / cell_m)
    slope_x, slope_z = np.gradient(z, cell_m)              # how fast the ground rises along x and z
    speed = wind_speed_ms(strength)
    a = np.radians(toward_deg)
    lift = speed * (np.cos(a) * slope_x + np.sin(a) * slope_z)   # m/s of air pushed upward

    # extra rain where air rises, less where it sinks; stronger wind = bigger contrast
    typical = np.abs(lift).mean() or 1.0
    share = np.maximum(MIN_SHARE, 1 + 0.25 * (0.5 + strength) * lift / typical)
    return average_rain_mm * share / share.mean()


def describe(rain, h, cell_m, toward_deg):
    """(windward mm, rain shadow mm): average rain on slopes facing the wind vs facing away."""
    z = gaussian_filter(climate.elevation_m(np.asarray(h, dtype=float)), SMOOTH_M / cell_m)
    slope_x, slope_z = np.gradient(z, cell_m)
    a = np.radians(toward_deg)
    facing = np.cos(a) * slope_x + np.sin(a) * slope_z
    lo, hi = np.percentile(facing, [25, 75])
    return float(rain[facing > hi].mean()), float(rain[facing < lo].mean())


def map_for_step(h, p, state, refresh_years=20000):
    """The rain map for a simulation step (yearly mm at every point), kept in `state` and only
    worked out again when the rain or wind changes, or after refresh_years (the terrain moves)."""
    key = (round(p['rain_mm'], -1), round(p.get('wind_strength', 0.0), 2),
           round(p.get('wind_toward', 0.0)))
    cached = state.get('rain_map')
    if (cached is None or cached.shape != h.shape or state.get('rain_key') != key
            or state.get('rain_age', 0) >= refresh_years):
        state['rain_map'] = rain_map(h, p['cell_m'], p['rain_mm'],
                                     p.get('wind_strength', 0.0), p.get('wind_toward', 0.0))
        state['rain_key'] = key
        state['rain_age'] = 0.0
    state['rain_age'] = state.get('rain_age', 0.0) + p['dt_days'] / 365
    return state['rain_map']
