"""conditions.py - the processes that change the land each step.
Each one is a function (heights, p) -> new heights; CONDITIONS lists them in run order
(a checkbox appears for each).
"""

import math

import numpy as np

import config
from erosion import river_erosion      # rivers cutting valleys + carrying sediment (erosion.py)
from vegetation import vegetation       # plants growing, protecting soil from rivers (vegetation.py)

MAX_RATE_PER_SUBSTEP = 0.5    # soil creep goes unstable above 1; 0.5 keeps a safe margin


def soil_creep(h, p):
    """Soil slides from high spots toward the average of its 4 neighbours."""
    years = p['dt_days'] / 365
    total = 4 * p['creep_d'] * years / p['cell_m'] ** 2
    substeps = max(1, math.ceil(total / MAX_RATE_PER_SUBSTEP))
    rate = total / substeps
    for _ in range(substeps):
        padded = np.pad(h, 1, mode='edge')
        up    = padded[:-2, 1:-1]
        down  = padded[2:,  1:-1]
        left  = padded[1:-1, :-2]
        right = padded[1:-1, 2:]
        average = (up + down + left + right) / 4
        h = h + rate * (average - h)
    return h


def uplift_pattern(shape):
    """How much each point is pushed up, from 0 at the map edges to 1 in the middle:
    one smooth dome, like a mountain range rising while the edges (rivers, sea) stay put."""
    rows, cols = shape
    across = np.sin(np.pi * np.arange(rows) / (rows - 1))
    down = np.sin(np.pi * np.arange(cols) / (cols - 1))
    return np.outer(across, down)


def tectonic_uplift(h, p):
    """The ground is pushed up by p['uplift_mm_yr'] mm per year in the middle of the map."""
    years = p['dt_days'] / 365
    rise_m = p['uplift_mm_yr'] / 1000 * years
    units_per_m = 255 / (config.MAX_ELEVATION_M - config.MIN_ELEVATION_M)
    return h + rise_m * units_per_m * uplift_pattern(h.shape)


# The conditions, in the order they run each step.
CONDITIONS = {
    'Soil creep': soil_creep,
    'Tectonic uplift': tectonic_uplift,
    'Vegetation': vegetation,
    'River erosion': river_erosion,
}


def run_conditions(h, p, enabled):
    """Run the named conditions (the ticked ones) once, in order."""
    for name in CONDITIONS:
        if name in enabled:
            h = CONDITIONS[name](h, p)
    return h
