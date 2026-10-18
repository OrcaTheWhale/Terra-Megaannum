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

To add a condition (rain, wind, plants...):
  1. write its function here (or in its own file and import it here)
  2. add it to CONDITIONS below
  3. put its numbers in PARAMS and UNCERTAINTY in config.py
A checkbox for it appears on screen automatically.
"""

import math

import numpy as np

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


# The conditions, in the order they run each step.
CONDITIONS = {
    'Soil creep': soil_creep,
}


def run_conditions(h, p, enabled):
    """Run the named conditions (the ticked ones) once, in order."""
    for name in CONDITIONS:
        if name in enabled:
            h = CONDITIONS[name](h, p)
    return h
