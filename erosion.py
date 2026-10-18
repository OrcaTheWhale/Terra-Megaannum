"""
erosion.py - rivers cutting valleys and carrying sediment downstream (the 'River erosion' condition).

Each step:
  1. DRAINAGE: which way water flows from every point (its "receiver", the lowest neighbour
     on the hollow-filled terrain) and how much land drains through it (drainage area A).
     This barely changes from one step to the next, so it's worked out again only after
     REROUTE_YEARS of simulated time or REROUTE_EVERY steps, whichever comes first (it's the
     slow part, ~25 ms; doing it every step gave nearly the same landscape in testing).
  2. EROSION (stream power law): a river cuts down at
         E = K * (A * wetness)^m * slope      (m = 0.5)
     More water and steeper slopes cut faster. Plants protect the ground: K is lowered by
     up to veg_protection (70%) where the vegetation cover is full. K comes from field measurements. Solved with
     the implicit method (Braun & Willett 2013, "FastScape"): working up from the river mouths,
     each point is solved exactly using its already-updated receiver, so even 10,000-year
     steps stay stable.
  3. SEDIMENT: the eroded soil is carried downstream, from the highest points to the lowest.
     Along the way a share of it settles out (deposition rate = G * sediment flux / A, the
     "xi-q" model of Davy & Lague 2009), so big, gentle rivers drop sediment and build flat
     valley floors. Lakes trap everything that reaches them until they're filled up (deltas).
     Whatever reaches the map edge is washed off the map, and counted.

Soil is conserved: eroded = deposited + washed off the map.

Speed trick: points are stored sorted by "level" (0 = river mouth at the map edge, 1 = drains
into a mouth, 2 = drains into a level-1 point, ...), so each level is one block of the arrays
and every level is worked out in one go with NumPy instead of one point at a time.
"""

import numpy as np

import climate
import config
import water

M = 0.5                  # drainage-area exponent in the stream power law (a common value)
REROUTE_EVERY = 25       # work out the drainage again at least every this many steps...
REROUTE_YEARS = 20000    # ...and at least every this many simulated years


def _route(h, state):
    """Work out the drainage for these heights and keep it in state (see module docstring)."""
    rows, cols = h.shape
    n = h.size
    filled = water.fill_depressions(h)
    rec = water.find_downhill(filled).ravel()          # receiver of each point, -1 = map edge outlet

    # level of each point. Lower points on the filled surface always come before the points
    # draining into them, so going from low to high, a receiver's level is always known.
    order = np.argsort(filled.ravel(), kind='stable').tolist()
    rec_list = rec.tolist()
    level = [0] * n
    for i in order:
        r = rec_list[i]
        if r >= 0:
            level[i] = level[r] + 1
    level = np.array(level)

    # put the points in level order; bounds[L]:bounds[L+1] is level L
    perm = np.argsort(level, kind='stable')            # sorted position -> original point
    where = np.empty(n, dtype=np.int64)
    where[perm] = np.arange(n)                         # original point -> sorted position
    rec_sorted = np.where(rec[perm] >= 0, where[np.maximum(rec[perm], 0)], -1)
    bounds = np.concatenate([[0], np.cumsum(np.bincount(level))])

    # drainage area (in points): each level passes its totals to the level below, top first
    area = np.ones(n)
    for L in range(len(bounds) - 2, 0, -1):
        a, b, a0 = bounds[L], bounds[L + 1], bounds[L - 1]
        area[a0:a] += np.bincount(rec_sorted[a:b] - a0, weights=area[a:b], minlength=a - a0)

    # distance to the receiver, in points (1 straight, 1.41 diagonal)
    pts = perm
    dist = np.ones(n)
    has = rec_sorted >= 0
    rp = perm[rec_sorted[has]]
    dist[has] = np.hypot(pts[has] // cols - rp // cols, pts[has] % cols - rp % cols)

    filled_sorted = filled.ravel()[perm]
    state.update(perm=perm, rec=rec_sorted, bounds=bounds, area=area, dist=dist,
                 filled=filled_sorted, lake=(filled_sorted - h.ravel()[perm]) > water.FLAT_SLOPE / 2,
                 shape=h.shape, steps_since_route=0, years_since_route=0.0)


def river_erosion(h, p):
    """One step of river erosion + sediment transport. p needs:
    river_k (1/yr), deposition_g, dt_days, cell_m, rain_mm, sea_temp, and a 'state' dict that
    lives as long as the simulation (it remembers the drainage between steps)."""
    state = p['state']
    if (state.get('shape') != h.shape or state['steps_since_route'] >= REROUTE_EVERY
            or state['years_since_route'] >= REROUTE_YEARS):
        _route(h, state)
    state['steps_since_route'] += 1
    state['years_since_route'] += p['dt_days'] / 365

    perm, rec, bounds = state['perm'], state['rec'], state['bounds']
    years = p['dt_days'] / 365
    m_per_unit = (config.MAX_ELEVATION_M - config.MIN_ELEVATION_M) / 255
    cell_m = p['cell_m']
    cell_area = cell_m ** 2

    # wetter climate = more water in the rivers = faster erosion (runoff from the Budyko curve)
    mean_temp = p['sea_temp'] - climate.LAPSE_RATE * climate.elevation_m(h.mean())
    runoff = climate.runoff_mm(p['rain_mm'], climate.lake_evaporation_mm(mean_temp))
    wetness = max(runoff, 0.0) / water.REF_RUNOFF_MM

    # 2. erosion: implicit stream power law, from the outlets (level 0) upward
    z_old = h.ravel()[perm] * m_per_unit              # metres, in level order
    z = z_old.copy()
    K = p['river_k']
    if state.get('veg') is not None:                  # plants hold the soil: slower erosion
        K = K * (1 - p.get('veg_protection', 0.0) * state['veg'].ravel()[perm])
    if p.get('rain_map') is not None:
        # wind-driven rain: each point adds its own runoff; add it up downstream like the area
        evap = climate.lake_evaporation_mm(mean_temp)
        discharge = climate.runoff_mm(p['rain_map'], evap).ravel()[perm] / water.REF_RUNOFF_MM
        for L in range(len(bounds) - 2, 0, -1):
            a, b, a0 = bounds[L], bounds[L + 1], bounds[L - 1]
            discharge[a0:a] += np.bincount(rec[a:b] - a0, weights=discharge[a:b], minlength=a - a0)
    else:
        discharge = state['area'] * wetness           # same rain everywhere
    F = K * years * (np.maximum(discharge, 0) * cell_area) ** M / (state['dist'] * cell_m)
    for L in range(1, len(bounds) - 1):
        a, b = bounds[L], bounds[L + 1]
        f = F[a:b]
        z[a:b] = np.minimum(z_old[a:b], (z_old[a:b] + f * z[rec[a:b]]) / (1 + f))
    eroded = z_old - z                                # metres cut down at each point

    # 3. sediment: carried downstream from the highest level, part of it settling on the way
    flux = np.zeros(h.size)                           # m3 of sediment arriving at each point
    settle_share = np.minimum(1.0, p['deposition_g'] / state['area'])   # G * cell area / A
    lake = state['lake']
    room = np.where(lake, np.maximum(state['filled'] * m_per_unit - z, 0), 0) * cell_area
    for L in range(len(bounds) - 2, 0, -1):
        a, b, a0 = bounds[L], bounds[L + 1], bounds[L - 1]
        carried = flux[a:b] + eroded[a:b] * cell_area
        settled = np.where(lake[a:b], np.minimum(carried, room[a:b]),   # lakes trap it
                           carried * settle_share[a:b])
        z[a:b] += settled / cell_area
        flux[a0:a] += np.bincount(rec[a:b] - a0, weights=carried - settled, minlength=a - a0)
    washed_off_m3 = flux[:bounds[1]].sum()            # reached the map edge (level 0)

    state['washed_off'] = state.get('washed_off', 0.0) + washed_off_m3 / (cell_area * m_per_unit)
    out = np.empty(h.size)
    out[perm] = z / m_per_unit
    return out.reshape(h.shape)
