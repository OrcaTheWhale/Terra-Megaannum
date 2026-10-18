"""
analysis.py - measuring the results: change scores, the likelihood score, charts and maps.
"""

import threading
import time

import matplotlib
matplotlib.use('Agg')                 # save charts to files, no pop-up windows
import matplotlib.pyplot as plt
import numpy as np

from config import (PARAMS, UNCERTAINTY, HEIGHT_ERROR, ENSEMBLE_RUNS,
                    ENSEMBLE_TIME_LIMIT, TOLERANCE, RELATIVE_TOLERANCE, MIN_CHANGE)
from conditions import run_conditions


def change_scores(h, original):
    """Two percentages: how much of the land has changed, and how much soil has moved."""
    difference = np.abs(h - original)
    land_changed = (difference > 1).mean() * 100
    soil_moved = (original - h).clip(min=0).sum() / original.sum() * 100
    return land_changed, soil_moved


class LikelihoodJob:
    """How likely is this result? Calculated in the background so the app doesn't freeze.

    Replays the whole simulation several times, each with slightly different but
    equally believable inputs (parameters nudged within UNCERTAINTY, every starting
    height nudged by up to HEIGHT_ERROR). Then, on the land that changed by more than
    MIN_CHANGE, it measures how often the runs changed it by the same amount (within
    RELATIVE_TOLERANCE, e.g. 25%). This is a Monte Carlo / ensemble method.
    The score is NaN if nothing has changed enough to score yet.

    Usage:
        job = LikelihoodJob(sim)    # starts straight away, in the background
        job.done_runs, job.total_runs   # progress
        job.result                  # (likelihood %, spread map, runs used) once finished
        job.cancel()                # stop early
    """

    def __init__(self, sim):
        # a frozen copy of everything needed, so the simulation can keep going meanwhile
        self.original = sim.original.copy()
        self.steps = list(sim.steps)
        self.target = sim.heights.copy()
        self.cell_m = sim.cell_m
        self.version = sim.version          # which state of the simulation this score is for
        self.done_runs = 0
        self.total_runs = ENSEMBLE_RUNS
        self.result = None
        self.cancelled = False
        threading.Thread(target=self._run, daemon=True).start()

    @property
    def finished(self):
        return self.result is not None

    def cancel(self):
        self.cancelled = True

    def _one_alternative_run(self, rng):
        base = {name: value * (1 + rng.uniform(-UNCERTAINTY.get(name, 0), UNCERTAINTY.get(name, 0)))
                for name, value in PARAMS.items()}
        h = self.original + rng.uniform(-HEIGHT_ERROR, HEIGHT_ERROR, self.original.shape)
        for n, s in enumerate(self.steps):        # replay exactly the same steps
            if n % 10 == 0:
                time.sleep(0.0005)    # let the drawing thread have a turn, so the app stays smooth
            p = dict(base)
            p['dt_days'] = s['dt_days']
            p['cell_m'] = self.cell_m
            p['day'] = s['start_day'] % 365
            p['sea_temp'] = s['sea_temp']
            h = run_conditions(h, p, s['enabled'])
        return h

    def _run(self):
        rng = np.random.default_rng()

        # time one run, then use as many runs as fit in the time limit (at least 5)
        t0 = time.perf_counter()
        finals = [self._one_alternative_run(rng)]
        per_run = max(time.perf_counter() - t0, 1e-6)
        self.total_runs = max(5, min(ENSEMBLE_RUNS, int(ENSEMBLE_TIME_LIMIT / per_run)))
        self.done_runs = 1
        for _ in range(self.total_runs - 1):
            if self.cancelled:
                return
            finals.append(self._one_alternative_run(rng))
            self.done_runs += 1

        finals = np.array(finals)
        change = self.target - self.original
        changed = np.abs(change) > MIN_CHANGE              # only score land that really changed
        if changed.any():
            allowed = np.maximum(TOLERANCE, RELATIVE_TOLERANCE * np.abs(change[changed]))
            agree = np.abs(finals[:, changed] - self.target[changed]) <= allowed
            score = agree.mean() * 100
        else:
            score = float('nan')
        spread = finals.std(axis=0)
        print(f'likelihood: {score:.1f}% over {self.total_runs} runs '
              f'({time.perf_counter() - t0:.1f} s)')
        self.result = (score, spread, self.total_runs)


# ---------------------------------------------------------------- saving pictures
def save_change_map(h, original, label):
    change = h - original
    biggest = abs(change).max() or 1
    plt.imshow(change, cmap='RdBu', vmin=-biggest, vmax=biggest)
    plt.colorbar(label='height change')
    plt.title(f'{label}: red = soil lost, blue = soil gained')
    plt.savefig('change_map.png')
    plt.close()
    print('saved change_map.png')


def save_history_chart(history):
    if not history:
        print('nothing simulated yet')
        return
    years = [row['days'] / 365 for row in history]
    fig, ax = plt.subplots()
    ax.plot(years, [row['land_changed'] for row in history], label='% of land changed')
    ax.plot(years, [row['soil_moved'] for row in history], label='% of soil moved')
    ax.set_xlabel('years simulated')
    ax.set_ylabel('%')
    ax.legend(loc='upper left')
    temps = ax.twinx()                     # temperature on a second axis, to see the seasons
    temps.plot(years, [row['sea_temp'] for row in history], color='gray', alpha=0.5)
    temps.set_ylabel('sea-level temperature (C)', color='gray')
    plt.title('Change over time')
    plt.savefig('history.png')
    plt.close()
    print('saved history.png')


def save_uncertainty_map(spread, score):
    if spread is None:
        print('run the likelihood check first (L)')
        return
    plt.imshow(spread, cmap='magma')
    plt.colorbar(label='disagreement between runs (height units)')
    label = f'likelihood {score:.0f}%' if score == score else 'nothing changed enough to score'   # NaN != NaN
    plt.title(f'Where the model is least sure ({label})')
    plt.savefig('uncertainty_map.png')
    plt.close()
    print('saved uncertainty_map.png')
