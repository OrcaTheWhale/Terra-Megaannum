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
                    ENSEMBLE_TIME_LIMIT, TOLERANCE)
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
    height nudged by up to HEIGHT_ERROR), then measures how often the runs end up
    within TOLERANCE of our result. This is a Monte Carlo / ensemble method.

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
        for s in self.steps:                      # replay exactly the same steps
            p = dict(base)
            p['dt_days'] = s['dt_days']
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
        agree = np.abs(finals - self.target) <= TOLERANCE
        score = agree.mean() * 100
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
    days = [row['days'] for row in history]
    fig, ax = plt.subplots()
    ax.plot(days, [row['land_changed'] for row in history], label='% of land changed')
    ax.plot(days, [row['soil_moved'] for row in history], label='% of soil moved')
    ax.set_xlabel('days simulated')
    ax.set_ylabel('%')
    ax.legend(loc='upper left')
    temps = ax.twinx()                     # temperature on a second axis, to see the seasons
    temps.plot(days, [row['sea_temp'] for row in history], color='gray', alpha=0.5)
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
    plt.title(f'Where the model is least sure (likelihood {score:.0f}%)')
    plt.savefig('uncertainty_map.png')
    plt.close()
    print('saved uncertainty_map.png')