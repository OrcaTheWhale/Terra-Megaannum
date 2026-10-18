"""hacks_law.py - checks our rivers against real ones (Hack's law: length = c * area^h,
h is about 0.5-0.6 for real rivers). Run: python hacks_law.py   (or with a seed: python hacks_law.py 42)
"""

import sys

import numpy as np

import config
import maps
import water
from simulation import Simulation

MIN_AREA_KM2 = 0.5        # only points with at least this much land draining in (real rivers)
HACK_C, HACK_H = 1.27, 0.6   # Hack's 1957 result, in km and km2


def measure(h, cell_m):
    """(A in km2, L in km) for every point of the map."""
    filled = water.fill_depressions(np.asarray(h, dtype=float))   # lakes fill, then overflow
    downhill = water.find_downhill(filled).ravel()
    n_cols = h.shape[1]
    area = np.full(h.size, (cell_m / 1000) ** 2)
    length = np.zeros(h.size)
    for i in np.argsort(-filled.ravel(), kind='stable'):          # highest first
        j = downhill[i]
        if j == -1:
            continue
        diagonal = (i // n_cols != j // n_cols) and (i % n_cols != j % n_cols)
        step = cell_m / 1000 * (np.sqrt(2) if diagonal else 1.0)
        area[j] += area[i]
        length[j] = max(length[j], length[i] + step)
    return area, length


def fit(area, length):
    """Hack exponent h and constant c from a straight line through log L vs log A."""
    keep = area >= MIN_AREA_KM2
    log_a, log_l = np.log10(area[keep]), np.log10(length[keep])
    edges = np.linspace(log_a.min(), log_a.max(), 15)
    which = np.digitize(log_a, edges)
    xs = [np.median(log_a[which == b]) for b in np.unique(which) if (which == b).sum() >= 3]
    ys = [np.median(log_l[which == b]) for b in np.unique(which) if (which == b).sum() >= 3]
    h, log_c = np.polyfit(xs, ys, 1)
    return h, 10 ** log_c, keep


def main():
    if len(sys.argv) > 1:
        start = maps.generate_heights(int(sys.argv[1])).astype(float)
        name = f'generated map (seed {sys.argv[1]})'
    else:
        first = list(config.MAPS)[0]
        start = maps.load_heightmap(config.MAPS[first][0])
        name = first

    sim = Simulation(start)
    print(f'Running 1,000,000 years on {name} (100 steps of 10,000 years)...')
    for _ in range(100):
        sim.advance(365 * 10_000, ['Soil creep', 'River erosion'])

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, (label, h) in zip(axes, [('Start', start), ('After 1 million years', sim.heights)]):
        area, length = measure(h, sim.cell_m)
        exponent, c, keep = fit(area, length)
        print(f'{label:<22} h = {exponent:.2f}   (L = {c:.2f} A^{exponent:.2f})   real rivers: 0.5-0.6')
        pick = np.flatnonzero(keep)
        pick = np.random.default_rng(0).choice(pick, min(3000, pick.size), replace=False)
        ax.loglog(area[pick], length[pick], '.', ms=3, alpha=0.35, color='#4a7fb5', label='each river point')
        a = np.logspace(np.log10(MIN_AREA_KM2), np.log10(area.max()), 50)
        ax.loglog(a, c * a ** exponent, color='#c0392b', lw=2.5, label=f'our rivers: h = {exponent:.2f}')
        ax.loglog(a, HACK_C * a ** HACK_H, '--', color='black', lw=1.5, label="Hack's law (real rivers): h = 0.6")
        ax.set_title(label)
        ax.set_xlabel('Area draining in, A (km²)')
        ax.grid(True, which='both', alpha=0.25)
        ax.legend(loc='upper left')
    axes[0].set_ylabel('River length, L (km)')
    fig.suptitle(f"Hack's law check: river length vs drainage area ({name})")
    fig.tight_layout()
    fig.savefig('hacks_law.png', dpi=150)
    print('Saved hacks_law.png')


if __name__ == '__main__':
    main()
