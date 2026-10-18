"""
analysis.py - measuring the results: change scores, the likelihood score, charts and maps.
"""

import threading
import time

import matplotlib
matplotlib.use('Agg')                 # save charts to files, no pop-up windows
import matplotlib.pyplot as plt
import numpy as np

import config
from config import (PARAMS, UNCERTAINTY, HEIGHT_ERROR, ENSEMBLE_RUNS,
                    ENSEMBLE_TIME_LIMIT, TOLERANCE, RELATIVE_TOLERANCE, MIN_CHANGE)

REPLAY_CHUNKS = 40       # alternative runs replay the history in at most this many longer steps
from conditions import run_conditions
import rain


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
        self.chunks = replay_chunks(sim.steps)
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
        state = {}                                # this run's own memory (river drainage)
        for s in self.chunks:                     # replay the same history
            time.sleep(0.001)         # let the drawing thread have a turn, so the app stays smooth
            p = dict(base)
            p.update(dt_days=s['dt_days'], cell_m=self.cell_m, day=s['start_day'] % 365,
                     sea_temp=s['sea_temp'], rain_mm=s['rain_mm'], sunlight=s['sunlight'],
                     mean_temp=s['mean_temp'], wind_strength=s['wind_strength'],
                     wind_toward=s['wind_toward'], state=state)
            p['rain_map'] = rain.map_for_step(h, p, state)
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


def replay_chunks(steps):
    """The history merged into at most REPLAY_CHUNKS longer steps, for fast replays.

    Neighbouring steps with the same conditions ticked are joined: their lengths add up and
    temperature and rain are averaged. Every condition handles long steps (creep with
    sub-steps, rivers with the implicit method), so the result is nearly the same, much faster.
    """
    if not steps:
        return []
    size = max(1, -(-len(steps) // REPLAY_CHUNKS))      # steps per chunk, rounded up
    chunks = []
    for s in steps:
        last = chunks[-1] if chunks else None
        if last and last['enabled'] == s['enabled'] and last['count'] < size:
            total = last['dt_days'] + s['dt_days']
            for name in ('sea_temp', 'rain_mm', 'sunlight', 'mean_temp'):
                last[name] = (last[name] * last['dt_days'] + s.get(name, last[name]) * s['dt_days']) / total
            last['dt_days'] = total
            last['count'] += 1
        else:
            chunks.append({'start_day': s['start_day'], 'dt_days': s['dt_days'], 'count': 1,
                           'sea_temp': s['sea_temp'], 'enabled': s['enabled'],
                           'rain_mm': s.get('rain_mm', config.ANNUAL_RAIN_MM),
                           'sunlight': s.get('sunlight', 1.0),
                           'mean_temp': s.get('mean_temp', config.AVG_TEMP_C),
                           'wind_strength': s.get('wind_strength', 0.0),
                           'wind_toward': s.get('wind_toward', 0.0)})
    return chunks


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
