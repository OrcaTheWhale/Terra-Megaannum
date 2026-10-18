"""simulation.py - time and history: runs each step and remembers every step
(so you can look back, rewind, and replay for the likelihood score).
"""

import numpy as np

import analysis
import climate
import config
from config import PARAMS
from conditions import run_conditions
import rain


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
        self.state = {}            # memory the conditions keep between steps (river drainage, soil washed off,
                                   # plant cover 'veg')
        self.veg_snapshots = [None]  # plant cover after each step (uint8 0-255), for looking back
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
        p['rain_mm'] = climate.current_rain_mm()
        p['sunlight'] = climate.sunlight
        p['mean_temp'] = config.AVG_TEMP_C + climate.warming_c
        p['wind_strength'] = climate.wind_strength
        p['wind_toward'] = climate.wind_toward
        p['state'] = self.state
        p['rain_map'] = rain.map_for_step(self.heights, p, self.state)   # wind-driven rain

        self.heights = run_conditions(self.heights, p, enabled)
        self.elapsed_days += dt_days

        # remember everything about this step
        self.steps.append({'start_day': start, 'dt_days': dt_days,
                           'sea_temp': p['sea_temp'], 'rain_mm': p['rain_mm'],
                           'sunlight': p['sunlight'], 'mean_temp': p['mean_temp'],
                           'wind_strength': p['wind_strength'], 'wind_toward': p['wind_toward'],
                           'enabled': tuple(enabled),
                           'washed_off': self.state.get('washed_off', 0.0)})
        self.snapshots.append(self.heights.astype(np.float32))
        veg = self.state.get('veg')
        self.veg_snapshots.append(None if veg is None else (veg * 255).astype(np.uint8))
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
        self.veg_snapshots = self.veg_snapshots[:step + 1]
        self.state = {'washed_off': self.washed_off_at(step)}   # drainage is worked out again
        if self.veg_at(step) is not None:
            self.state['veg'] = self.veg_at(step)
        self.version += 1
        self.timeline += 1

    def heights_at(self, step):
        return self.snapshots[step].astype(float)

    def veg_at(self, step):
        """Plant cover (0-1) after this step, or None if vegetation wasn't on then."""
        if step == self.step and self.state.get('veg') is not None:
            return self.state['veg']                 # latest (may include a fire right now)
        snap = self.veg_snapshots[step] if step < len(self.veg_snapshots) else None
        return None if snap is None else snap.astype(float) / 255

    def washed_off_at(self, step):
        """Soil washed off the map edge by rivers up to this step (in height units, summed)."""
        return self.steps[step - 1].get('washed_off', 0.0) if step > 0 else 0.0

    def days_at(self, step):
        return sum(s['dt_days'] for s in self.steps[:step])

    def sea_temp_at(self, step):
        """Sea-level temperature during the step that led to this point."""
        if step == 0:
            return climate.sea_level_temp(0, 1)
        return self.steps[step - 1]['sea_temp']
