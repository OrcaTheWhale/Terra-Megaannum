"""water.py - rivers and lakes: fill hollows, find downhill, add up the flow; lakes shrink
until inflow = evaporation. Drawn as a second terrain mesh worked out in the background.
"""

import heapq
import threading

import numpy as np
from scipy.ndimage import label

import climate
import config

# Change these settings here, not in main.py.
RIVER_MIN_AREA_KM2 = 0.5   # a river starts where this much land drains through a point
LAKE_MIN_DEPTH = 0.3       # hollows shallower than this (height units) don't count as lakes
LAKE_MIN_AREA_KM2 = 0.1    # smaller ponds aren't drawn (water still flows through them)
REF_RUNOFF_MM = 300        # at this much runoff a river starts at RIVER_MIN_AREA_KM2; drier = fewer rivers
RIVER_DEPTH = 0.5          # how high a small river is drawn above the ground (height units)
HIDDEN_DEPTH = 1.0         # dry places: the water surface hides this far below the ground
FLOW_SPEED = 0.03          # speed of animated ripples
FLAT_SLOPE = 1e-4          # tiny slope added across lake surfaces so water can cross them


def fill_depressions(heights):
    """Fill every hollow up to the level where it would spill over (priority-flood)."""
    h = np.asarray(heights, dtype=float)
    rows, cols = h.shape
    filled = h.ravel().tolist()
    done = bytearray(rows * cols)
    queue = []
    for i in range(rows * cols):
        r, c = divmod(i, cols)
        if r == 0 or r == rows - 1 or c == 0 or c == cols - 1:   # the map's edge
            queue.append((filled[i], i))
            done[i] = 1
    heapq.heapify(queue)
    while queue:
        level, i = heapq.heappop(queue)           # the lowest point reached so far
        r, c = divmod(i, cols)
        for nr in (r - 1, r, r + 1):
            if not 0 <= nr < rows:
                continue
            for nc in (c - 1, c, c + 1):
                if not 0 <= nc < cols:
                    continue
                j = nr * cols + nc
                if done[j]:
                    continue
                done[j] = 1
                if filled[j] < level + FLAT_SLOPE:    # lower than where we came from: in a hollow
                    filled[j] = level + FLAT_SLOPE
                heapq.heappush(queue, (filled[j], j))
    return np.array(filled).reshape(rows, cols)


def find_downhill(heights, diagonals=True):
    """Return the flattened index of each cell's lowest downhill neighbour (-1 = none)."""
    h = np.asarray(heights, dtype=float)
    nr, nc = h.shape
    padded = np.pad(h, 1, mode='constant', constant_values=np.inf)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonals:
        directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    neighbours = np.stack([
        padded[1 + dr:1 + dr + nr, 1 + dc:1 + dc + nc]
        for dr, dc in directions
    ])
    choice = np.argmin(neighbours, axis=0)
    lowest = np.take_along_axis(neighbours, choice[None], axis=0)[0]
    r, c = np.indices(h.shape)
    dr = np.array([d[0] for d in directions])
    dc = np.array([d[1] for d in directions])
    receiver = (r + dr[choice]) * nc + c + dc[choice]
    return np.where(lowest < h, receiver, -1).astype(np.int64)


def flow_amount(heights, downhill, weights=None):
    """Count upstream rainfall reaching each cell along downhill paths.
    weights: how much water each point adds (default 1 each, i.e. drainage area in points)."""
    h = np.asarray(heights, dtype=float)
    receivers = np.asarray(downhill).ravel()
    flow = np.ones(h.size, dtype=float) if weights is None else np.asarray(weights, dtype=float).ravel().copy()
    # Higher cells are processed first, so all upstream water arrives before
    # any lower cell passes its accumulated flow onward.
    for i in np.argsort(-h.ravel(), kind='stable'):
        j = receivers[i]
        if j != -1:
            flow[j] += flow[i]
    return flow.reshape(h.shape)


def find_water(heights, rain_mm=None, sea_temp=None, rain_map=None):
    """Where the water is. Returns (filled, lakes, rivers, flow, min_flow, info)."""
    h = np.asarray(heights, dtype=float)
    filled = fill_depressions(h)
    downhill = find_downhill(filled)
    flow = flow_amount(filled, downhill)
    cell_m = config.MAP_WIDTH_M / (h.shape[0] - 1)           # metres between points
    cell_km2 = (cell_m / 1000) ** 2
    surface = filled.copy()
    info = {'closed': 0, 'runoff': None, 'evaporation': None}
    min_flow = max(2.0, RIVER_MIN_AREA_KM2 / cell_km2)

    if rain_mm is not None and sea_temp is not None:
        mean_temp = sea_temp - climate.LAPSE_RATE * climate.elevation_m(h.mean())
        info['evaporation'] = climate.lake_evaporation_mm(mean_temp)
        runoff = climate.runoff_mm(rain_mm, info['evaporation'])
        info['runoff'] = runoff
        if rain_map is not None:
            # each point adds its own runoff (measured in "points of land at REF_RUNOFF_MM")
            weights = climate.runoff_mm(rain_map, info['evaporation']) / REF_RUNOFF_MM
            flow = flow_amount(filled, downhill, weights)
        else:
            weights = None
            min_flow *= REF_RUNOFF_MM / max(runoff, 1e-6)    # drier climate: fewer rivers

        # every hollow (filled above the ground), numbered; diagonal neighbours count as touching
        hollow = (filled - h) > FLAT_SLOPE / 2
        numbered, count = label(hollow, structure=np.ones((3, 3)))
        flat_numbers = numbered.ravel()
        order = np.argsort(flat_numbers, kind='stable')
        starts = np.searchsorted(flat_numbers[order], np.arange(1, count + 2))
        h_flat, flow_flat, filled_flat = h.ravel(), flow.ravel(), filled.ravel()
        surface_flat = surface.ravel()
        for k in range(count):
            cells = order[starts[k]:starts[k + 1]]
            spill_level = filled_flat[cells].max()
            lake_temp = sea_temp - climate.LAPSE_RATE * climate.elevation_m(spill_level)
            evaporation = climate.lake_evaporation_mm(lake_temp)
            rain_here = rain_mm if rain_map is None else float(rain_map.ravel()[cells].mean())
            if evaporation <= rain_here:
                continue                                     # more rain than evaporation: fills up
            if rain_map is None:
                inflow = runoff * flow_flat[cells].max()     # mm x points per year draining in
                runoff_here = runoff
            else:
                inflow = flow_flat[cells].max() * REF_RUNOFF_MM   # each point's own runoff, added up
                runoff_here = climate.runoff_mm(rain_here, info['evaporation'])
            # balance: inflow - runoff*A (lake area isn't land) + rain*A = evaporation*A  ->  A = ...
            area_needed = inflow / (evaporation - rain_here + runoff_here)
            if area_needed >= len(cells):
                continue                                     # it fills to the rim and overflows
            info['closed'] += 1
            ground = np.sort(h_flat[cells])
            n = int(area_needed)
            level = ground[n - 1] + FLAT_SLOPE if n >= 1 else ground[0] - 1   # n = 0: dry basin
            surface_flat[cells] = np.maximum(h_flat[cells], level)
        if info['closed']:
            # closed lakes keep their water: route the flow again on the new surface,
            # so nothing flows out of them and the rivers below get less
            downhill = find_downhill(surface)
            flow = flow_amount(surface, downhill, weights)

    # lakes: deep enough, and big enough (each separate lake gets a number, then we count its points)
    lakes = (surface - h) > LAKE_MIN_DEPTH
    numbered, count = label(lakes)
    sizes = np.bincount(numbered.ravel())
    big_enough = sizes * cell_km2 >= LAKE_MIN_AREA_KM2
    big_enough[0] = False                                     # number 0 = not a lake
    lakes = big_enough[numbered]

    rivers = (flow >= min_flow) & ~lakes
    rivers, flow = connect_diagonals(rivers, flow, surface, downhill)
    rivers &= ~lakes
    return surface, lakes, rivers, flow, min_flow, info


def connect_diagonals(rivers, flow, filled, downhill):
    """Make rivers that run diagonally draw as one connected line."""
    rows, cols = rivers.shape
    downhill = np.asarray(downhill).ravel()
    src = np.flatnonzero(rivers.ravel() & (downhill >= 0))
    dst = downhill[src]
    r0, c0 = np.divmod(src, cols)
    r1, c1 = np.divmod(dst, cols)
    diagonal = (r0 != r1) & (c0 != c1)
    r0, c0, r1, c1, src = r0[diagonal], c0[diagonal], r1[diagonal], c1[diagonal], src[diagonal]
    # the two corner points beside the diagonal step: (r1, c0) and (r0, c1)
    use_first = filled[r1, c0] <= filled[r0, c1]
    cr = np.where(use_first, r1, r0)
    cc = np.where(use_first, c0, c1)
    rivers = rivers.copy()
    flow = flow.copy()
    rivers[cr, cc] = True
    flow[cr, cc] = np.maximum(flow[cr, cc], flow.ravel()[src])   # same width as the river
    return rivers, flow


def water_surface(heights, rain_mm=None, sea_temp=None, wind_strength=0.0, wind_toward=0.0):
    """Height of the water surface at every point (below the ground where it's dry).
    Returns (surface, lakes, rivers, info). Wind makes the rain uneven (rain.py)."""
    import rain
    h = np.asarray(heights, dtype=float)
    rain_map = None
    if rain_mm is not None and wind_strength >= 0.05:
        cell_m = config.MAP_WIDTH_M / (h.shape[0] - 1)
        rain_map = rain.rain_map(h, cell_m, rain_mm, wind_strength, wind_toward)
    filled, lakes, rivers, flow, min_flow, info = find_water(h, rain_mm, sea_temp, rain_map)
    surface = h - HIDDEN_DEPTH                                 # dry: hidden under the ground
    # bigger rivers are drawn deeper/wider: depth grows with log of the flow
    river_depth = RIVER_DEPTH * (1 + np.log2(np.maximum(flow / min_flow, 1)) / 3)
    surface = np.where(rivers, h + river_depth, surface)
    surface = np.where(lakes, filled, surface)                # lakes are flat at their water level
    return surface, lakes, rivers, info


def make_flow_texture(size=128):
    """Make a blue rippling texture entirely in memory; no image file needed."""
    from PIL import Image
    from ursina import Texture
    from panda3d.core import SamplerState

    u = np.arange(size, dtype=float)[None, :] / size
    v = np.arange(size, dtype=float)[:, None] / size
    waviness = 0.12 * np.sin(2 * np.pi * 2 * v)
    crest = (0.5 + 0.5 * np.cos(2 * np.pi * (5 * u + waviness))) ** 8
    shimmer = 0.5 + 0.5 * np.sin(2 * np.pi * (3 * u - v))

    pixels = np.empty((size, size, 4), dtype=np.uint8)
    pixels[..., 0] = np.clip(22 + 28 * crest + 5 * shimmer, 0, 255)
    pixels[..., 1] = np.clip(113 + 48 * crest + 9 * shimmer, 0, 255)
    pixels[..., 2] = np.clip(184 + 38 * crest + 7 * shimmer, 0, 255)
    pixels[..., 3] = 255

    tex = Texture(Image.fromarray(pixels, mode='RGBA'))
    tex._texture.setWrapU(SamplerState.WM_repeat)
    tex._texture.setWrapV(SamplerState.WM_repeat)
    tex.filtering = 'bilinear'
    return tex


class RiverSystem:
    """The water surface, drawn as a second terrain mesh on top of the real one."""

    def __init__(self, original_heights, scale, climate_now=(None, None)):
        from ursina import color
        from TerrainHandler import FastTerrain

        surface, lakes, rivers, info = water_surface(original_heights, *climate_now)
        from terrain_shader import water_shader
        self.entity = FastTerrain(surface, scale=scale, texture=make_flow_texture(),
                                  color=color.white, double_sided=True, shader=water_shader)
        self.entity.set_shader_input('freeze_line', 2.0)    # main.py moves it with the climate (ice)
        self.elapsed = 0.0
        self.job = None           # (thread, heights, key, result) while water is being worked out
        self.updates = 0          # how many times new water has been shown
        self.pending = None       # the newest request waiting for its turn
        self.depth = surface - np.asarray(original_heights, dtype=float)
        entry = (surface, 100 * lakes.mean(), 100 * rivers.mean(), info)
        self.cache = {('original', climate_now): entry}      # O key is instant
        self.lake_percent, self.river_percent, self.info = entry[1], entry[2], info
        print(f'Water: lakes {self.lake_percent:.1f}% of map, rivers {self.river_percent:.1f}%')

    CACHE_SIZE = 300          # remember the water for this many terrains (each is tiny)

    def request(self, heights, key=None, climate_now=(None, None)):
        """Show the water for these heights, without making the app wait."""
        h = np.asarray(heights, dtype=float)
        if key is not None:
            key = (key, climate_now)          # the same terrain in another climate has other lakes
        if key is not None and key in self.cache:
            self.pending = None
            self._show(h, *self.cache[key])
            return
        self.follow(h)
        self.pending = (h.copy(), key, climate_now)        # only the newest request matters
        self._start_next()

    def _start_next(self):
        if self.job is not None or self.pending is None:
            return
        h, key, climate_now = self.pending
        self.pending = None
        result = {}

        def work():
            result['water'] = water_surface(h, *climate_now)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        self.job = (thread, h, key, result)

    def _poll(self):
        """Every frame: if a background calculation has finished, show it."""
        if self.job is None or self.job[0].is_alive():
            return
        thread, h, key, result = self.job
        self.job = None
        if 'water' in result:
            surface, lakes, rivers, info = result['water']
            entry = (surface, 100 * lakes.mean(), 100 * rivers.mean(), info)
            if key is not None:
                if len(self.cache) >= self.CACHE_SIZE:
                    self.cache.pop(next(iter(self.cache)))      # forget the oldest one
                self.cache[key] = entry
            self._show(h, *entry)
        self._start_next()                    # a newer request came in meanwhile

    def _show(self, heights, surface, lake_percent, river_percent, info):
        self.updates += 1                     # shown on screen, to see the water keeping up
        self.info = info
        self.entity.set_heights(surface)
        self.depth = surface - heights        # remembered for follow()
        self.lake_percent = lake_percent
        self.river_percent = river_percent

    def follow(self, heights):
        """Cheap redraw: keep the rivers and lakes where they were last worked out, but move
        them up/down with the changing ground so they don't sink into it or float above it."""
        self.entity.set_heights(heights + self.depth)

    @property
    def enabled(self):
        return self.entity.enabled

    @enabled.setter
    def enabled(self, value):
        self.entity.enabled = value

    def update(self, dt):
        """Every frame: pick up finished water, and animate the ripples by sliding the
        texture (cheap: nothing is rebuilt)."""
        self._poll()
        self.elapsed = (self.elapsed + max(0.0, dt) * FLOW_SPEED) % 1.0
        self.entity.texture_offset = (self.elapsed, self.elapsed * 0.4)
