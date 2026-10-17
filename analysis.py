"""
analysis.py - measuring the results: change scores, the likelihood score, charts and maps.
"""

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


def likelihood(sim):
    """How likely is this result?

    Replays the whole simulation several times, each with slightly different but
    equally believable inputs (parameters nudged within UNCERTAINTY, every starting
    height nudged by up to HEIGHT_ERROR), then measures how often the runs end up
    within TOLERANCE of our result. This is a Monte Carlo / ensemble method.

    Returns (likelihood %, spread map, number of runs used).
    """
    rng = np.random.default_rng()

    def one_alternative_run():
        base = {name: value * (1 + rng.uniform(-UNCERTAINTY.get(name, 0), UNCERTAINTY.get(name, 0)))
                for name, value in PARAMS.items()}
        h = sim.original + rng.uniform(-HEIGHT_ERROR, HEIGHT_ERROR, sim.original.shape)
        for s in sim.steps:                       # replay exactly the same steps
            p = dict(base)
            p['dt_days'] = s['dt_days']
            p['day'] = s['start_day'] % 365
            p['sea_temp'] = s['sea_temp']
            h = run_conditions(h, p, s['enabled'])
        return h

    # time one run, then use as many runs as fit in the time limit (at least 5)
    t0 = time.perf_counter()
    finals = [one_alternative_run()]
    per_run = max(time.perf_counter() - t0, 1e-6)
    runs = max(5, min(ENSEMBLE_RUNS, int(ENSEMBLE_TIME_LIMIT / per_run)))
    for _ in range(runs - 1):
        finals.append(one_alternative_run())

    finals = np.array(finals)
    agree = np.abs(finals - sim.heights) <= TOLERANCE
    score = agree.mean() * 100
    spread = finals.std(axis=0)
    print(f'likelihood: {score:.1f}% over {runs} runs ({per_run * runs:.1f} s)')
    return score, spread, runs


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