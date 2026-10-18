"""
simulation.py - keeps track of time and everything that has happened.

The Simulation remembers every step it has taken (how long it was, which
conditions were ticked, the temperature) and the terrain after each step,
so you can look back through time, rewind, and replay for the likelihood score.
"""

import numpy as np

import analysis
import climate
import config
from config import PARAMS
from conditions import run_conditions


class Simulation:
    def __init__(self, original):
        self.original = original
        self.cell_m = config.MAP_WIDTH_M / (original.shape[0] - 1)   # metres between neighbouring points
        self.version = 0           # goes up every time the terrain changes
        self.timeline = 0          # goes up only when history is thrown away (reset / rewind),
                                   # so (timeline, step) always means the same terrain
        self.reset()

    def reset(self):
        """Back to the start."""
        self.heights = self.original.copy()
        self.elapsed_days = 0.0
        self.steps = []                                      # one record per step taken
        self.snapshots = [self.original.astype(np.float32)]  # terrain after each step (index 0 = start)
        self.history = []                                    # numbers per step, for charts
        self.version += 1
        self.timeline += 1

    @property
    def step(self):
        """How many steps have been taken."""
        return len(self.steps)

    def advance(self, dt_days, enabled):
        """Take one step of dt_days, running the ticked conditions."""
        start = self.elapsed_days
        p = dict(PARAMS)
        p['dt_days'] = dt_days
        p['cell_m'] = self.cell_m
        p['day'] = start % climate.YEAR
        p['sea_temp'] = climate.sea_level_temp(start, dt_days)

        self.heights = run_conditions(self.heights, p, enabled)
        self.elapsed_days += dt_days

        # remember everything about this step
        self.steps.append({'start_day': start, 'dt_days': dt_days,
                           'sea_temp': p['sea_temp'], 'enabled': tuple(enabled)})
        self.snapshots.append(self.heights.astype(np.float32))
        land_changed, soil_moved = analysis.change_scores(self.heights, self.original)
        self.history.append({'step': self.step, 'days': self.elapsed_days,
                             'land_changed': land_changed, 'soil_moved': soil_moved,
                             'sea_temp': p['sea_temp']})
        self.version += 1

    def rewind_to(self, step):
        """Go back to an earlier step; everything after it is forgotten."""
        self.heights = self.snapshots[step].astype(float)
        self.steps = self.steps[:step]
        self.snapshots = self.snapshots[:step + 1]
        self.history = self.history[:step]
        self.elapsed_days = sum(s['dt_days'] for s in self.steps)
        self.version += 1
        self.timeline += 1

    def heights_at(self, step):
        return self.snapshots[step].astype(float)

    def days_at(self, step):
        return sum(s['dt_days'] for s in self.steps[:step])

    def sea_temp_at(self, step):
        """Sea-level temperature during the step that led to this point."""
        if step == 0:
            return climate.sea_level_temp(0, 1)
        return self.steps[step - 1]['sea_temp']
