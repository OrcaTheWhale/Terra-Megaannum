"""
vegetation.py - plants and forests (the 'Vegetation' condition), and fire.

Plant cover is a number from 0 (bare ground) to 1 (dense forest) at every point. It's kept in
the simulation's state, not in the heights, because it doesn't move soil itself: it PROTECTS
soil, making river erosion slower where plants are thick (roots hold the ground).

Each step:
  1. CARRYING CAPACITY: the most plant cover each point can support, from
        temperature   too cold above the treeline (yearly mean below about -4 C: no plants)
        rain          deserts (under ~150 mm a year) support almost nothing; ~800 mm+ is full
        slope         cliffs steeper than ~55 degrees hold no soil, so no plants
  2. GROWTH: logistic growth toward that capacity,
        dV/dt = r * V * (1 - V / capacity)
     fast when sparse, slowing as it fills up. r is faster with more sunlight (light sensor).
     Solved exactly for any step length, so a 1,000-year step just reaches the capacity.
  3. SPREADING: plants creep into neighbouring ground (seeds), so a burned patch regrows
     from its edges inward. Growth + spreading together is the Fisher-KPP equation.

Fire (flame sensor or the B key) burns the plants in a patch. Regrowth takes decades, so it's
only visible with Day / Season / Year steps - with 1,000-year steps the forest is always
back by the next step. That's "separation of timescales": plants are fast, terrain is slow.
"""

import numpy as np

import climate
import config

TREELINE_C = -4.0        # yearly mean temperature where plants stop (real treelines: about -6 to 0 C)
FULL_GROWTH_C = 2.0      # ...and where they reach full cover
DESERT_MM = 150          # yearly rain below which almost nothing grows
LUSH_MM = 800            # yearly rain for full cover
CLIFF_START_DEG = 35     # slopes steeper than this start losing plant cover...
CLIFF_BARE_DEG = 55      # ...and are bare at this
SEED_COVER = 0.01        # cover that seeds give bare (but growable) ground each step


def _clip01(x):
    return np.clip(x, 0.0, 1.0)


def slope_degrees(h, cell_m):
    """Real slope of the ground at every point, in degrees."""
    z = climate.elevation_m(h)
    gx, gz = np.gradient(z, cell_m)
    return np.degrees(np.arctan(np.hypot(gx, gz)))


def capacity(h, cell_m, sea_temp_mean, rain_mm):
    """The most plant cover (0-1) each point can support: temperature x rain x slope."""
    temp = sea_temp_mean - climate.LAPSE_RATE * climate.elevation_m(h)
    warm = _clip01((temp - TREELINE_C) / (FULL_GROWTH_C - TREELINE_C))
    wet = _clip01((np.asarray(rain_mm, dtype=float) - DESERT_MM) / (LUSH_MM - DESERT_MM))   # number or map
    flat = _clip01((CLIFF_BARE_DEG - slope_degrees(h, cell_m)) / (CLIFF_BARE_DEG - CLIFF_START_DEG))
    return warm * wet * flat


def vegetation(h, p):
    """One step of plant growth. Changes p['state']['veg'], not the heights."""
    state = p['state']
    years = p['dt_days'] / 365
    # plants respond to the yearly climate, not one day's weather
    mean_temp = config.AVG_TEMP_C + climate.warming_c if p.get('mean_temp') is None else p['mean_temp']
    rain_here = p['rain_map'] if p.get('rain_map') is not None else p['rain_mm']
    cap = capacity(h, p['cell_m'], mean_temp, rain_here)
    veg = state.get('veg')
    if veg is None or veg.shape != h.shape:
        veg = cap.copy()                                  # start as a mature landscape

    # spreading: move toward the neighbours' average (diffusion, like soil creep), in real units:
    # share = D * t / cell^2, at most 1/4 per step (more would overshoot; long steps are at capacity anyway)
    share = min(0.25, p['veg_spread'] * years / p['cell_m'] ** 2)
    padded = np.pad(veg, 1, mode='edge')
    neighbours = (padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]) / 4
    veg = veg + share * (neighbours - veg)

    # growth: exact solution of the logistic equation over this step
    r = p['veg_growth'] * p.get('sunlight', 1.0)
    veg = np.maximum(veg, SEED_COVER * (cap > 0))         # seeds land on any growable ground
    decay = np.exp(-r * years)
    safe_cap = np.maximum(cap, 1e-6)
    grown = safe_cap / (1 + (safe_cap - veg) / np.maximum(veg, 1e-9) * decay)  # also shrinks if over capacity
    veg = np.where(cap > 1e-6, grown, veg * decay)        # nothing can grow here: plants die off
    state['veg'] = _clip01(veg)
    return h


def burn(veg, h_shape, x_frac, z_frac, radius_frac=0.1, strength=0.5):
    """Fire: plant cover in a circle around (x_frac, z_frac) (0-1 across the map) drops by
    `strength` (0.5 = half burns each time this is called)."""
    n, m = h_shape
    i, j = np.ogrid[:n, :m]
    d = np.hypot(i / (n - 1) - x_frac, j / (m - 1) - z_frac)
    inside = d < radius_frac
    veg = veg.copy()
    veg[inside] *= (1 - strength)
    return veg
