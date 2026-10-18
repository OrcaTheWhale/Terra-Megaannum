"""
conditions.py - the physics. Each condition changes the land during one step.

Every condition is a function  condition(h, p) -> new h
    h  the heights (NumPy array, 0-255 scale)
    p  a dictionary with:
         everything in PARAMS (config.py), e.g. p['creep_d']
         p['dt_days']    how many days this step covers (1 day up to 10,000 years)
         p['cell_m']     real distance between neighbouring points, in metres
         p['day']        day of the year this step starts on
         p['sea_temp']   average sea-level temperature during this step (C)
         p['rain_mm']    yearly rain during this step (mm)
         p['state']      a dict that lasts the whole simulation, for conditions that need
                         to remember things between steps (river erosion keeps its drainage here)

To add a condition (rain, wind, plants...):
  1. write its function here (or in its own file and import it here)
  2. add it to CONDITIONS below
  3. put its numbers in PARAMS and UNCERTAINTY in config.py
A checkbox for it appears on screen automatically.
"""

import math

import numpy as np

import config
from erosion import river_erosion      # rivers cutting valleys + carrying sediment (erosion.py)
from vegetation import vegetation       # plants growing, protecting soil from rivers (vegetation.py)

MAX_RATE_PER_SUBSTEP = 0.5    # soil creep goes unstable above 1; 0.5 keeps a safe margin


def soil_creep(h, p):
    """Soil slides from high spots toward the average of its 4 neighbours.

    This is the diffusion equation  dh/dt = D * laplacian(h), with D in m^2/year.
    On our grid it becomes: each point moves toward its neighbours' average by
        rate = 4 * D * (time in years) / (distance between points)^2
    Real D is tiny, so visible change takes hundreds of thousands of years.

    A big step in one go makes the maths unstable (the terrain explodes into spikes),
    so a long step is split into enough small sub-steps to stay stable.
    """
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
    """The ground is pushed up by p['uplift_mm_yr'] mm per year in the middle of the map.

    Without uplift, every run could only ever flatten the land. Soil creep alone is far too
    slow to balance it on a map this size (it would take ~20 billion years to reshape 10 km),
    so with only creep + uplift the mountains keep growing. In real landscapes it's mainly
    rivers (and landslides) that cut mountains down fast enough to balance uplift: with
    river erosion added, long runs can reach a "steady state" where the shape stops changing
    while rock keeps flowing through it.
    """
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
