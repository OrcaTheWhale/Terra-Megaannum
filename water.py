"""
water.py - rivers and lakes: where rain water goes on the current terrain, and drawing it.

How it works (each time the terrain changes):
  1. Fill the hollows. Rain that runs into a hollow fills it up until it spills over
     the lowest point of its rim - that's a lake. (Priority-flood algorithm.)
  2. Find downhill. Every point sends its water to its lowest neighbour (8 directions).
  3. Add up the flow. Going from the highest point to the lowest, each point passes
     on all the water it has collected. Flow = how many points drain through here.
  4. Rivers are where enough land drains through a point (RIVER_MIN_AREA_KM2).

Drawing: the water is a second copy of the terrain mesh (same grid, same triangles).
Where there's water, its surface sits above the ground; everywhere else it sits just
below the ground, so it's hidden. Because both meshes share the exact same triangles,
the river and lake edges come out smooth instead of blocky.

The water is only drawn - it doesn't move soil yet (that will be a 'Rivers' condition).

main.py only needs:
    rivers = RiverSystem(original_heights, scale=config.SCALE)
    rivers.request(heights, key)   # whenever the terrain is redrawn (key: see request)
    rivers.update(time.dt)        # every frame (animates the ripples)
"""

import heapq
import threading

import numpy as np
from scipy.ndimage import label

import config

# Change these settings here, not in main.py.
RIVER_MIN_AREA_KM2 = 0.5   # a river starts where this much land drains through a point
LAKE_MIN_DEPTH = 0.3       # hollows shallower than this (height units) don't count as lakes
LAKE_MIN_AREA_KM2 = 0.1    # smaller ponds aren't drawn (water still flows through them)
RIVER_DEPTH = 0.5          # how high a small river is drawn above the ground (height units)
HIDDEN_DEPTH = 1.0         # dry places: the water surface hides this far below the ground
FLOW_SPEED = 0.03          # speed of animated ripples
FLAT_SLOPE = 1e-4          # tiny slope added across lake surfaces so water can cross them


def fill_depressions(heights):
    """Fill every hollow up to the level where it would spill over (priority-flood).

    Start from the map's edge (water can always leave there) and work inwards, always
    from the lowest point reached so far. A neighbour that's lower than where we came
    from must be in a hollow, so it's raised to that level (plus a tiny slope so water
    can still flow across the lake surface).
    (Uses plain Python lists instead of NumPy inside the loop: indexing them is faster.)
    """
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


def flow_amount(heights, downhill):
    """Count upstream rainfall reaching each cell along downhill paths."""
    h = np.asarray(heights, dtype=float)
    receivers = np.asarray(downhill).ravel()
    flow = np.ones(h.size, dtype=float)
    # Higher cells are processed first, so all upstream water arrives before
    # any lower cell passes its accumulated flow onward.
    for i in np.argsort(-h.ravel(), kind='stable'):
        j = receivers[i]
        if j != -1:
            flow[j] += flow[i]
    return flow.reshape(h.shape)


def find_water(heights):
    """Where the water is. Returns (filled, lakes, rivers, flow, min_flow).

    filled   the terrain with hollows filled to their spill level
    lakes    True where a hollow is deep enough to count as a lake
    rivers   True where enough land drains through to make a river
    flow     how many points drain through each point
    min_flow how many points of land a river needs (from RIVER_MIN_AREA_KM2)
    """
    h = np.asarray(heights, dtype=float)
    filled = fill_depressions(h)
    downhill = find_downhill(filled)
    flow = flow_amount(filled, downhill)
    cell_m = config.MAP_WIDTH_M / (h.shape[0] - 1)           # metres between points
    cell_km2 = (cell_m / 1000) ** 2

    # lakes: deep enough, and big enough (each separate lake gets a number, then we count its points)
    lakes = (filled - h) > LAKE_MIN_DEPTH
    numbered, count = label(lakes)
    sizes = np.bincount(numbered.ravel())
    big_enough = sizes * cell_km2 >= LAKE_MIN_AREA_KM2
    big_enough[0] = False                                     # number 0 = not a lake
    lakes = big_enough[numbered]

    min_flow = max(2.0, RIVER_MIN_AREA_KM2 / cell_km2)
    rivers = (flow >= min_flow) & ~lakes
    rivers, flow = connect_diagonals(rivers, flow, filled, downhill)
    rivers &= ~lakes
    return filled, lakes, rivers, flow, min_flow


def connect_diagonals(rivers, flow, filled, downhill):
    """Make rivers that run diagonally draw as one connected line.

    Water can flow diagonally (8 directions), so a river can be a chain of points that only
    touch at their corners. The 3D mesh splits each square into two triangles along one
    diagonal, so chains running along the OTHER diagonal were drawn as separate dots.
    For every diagonal step, also mark the lower of the two points beside it, so the river
    is connected side-to-side. (This only changes the drawing, not where water goes.)
    """
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


def water_surface(heights):
    """Height of the water surface at every point (below the ground where it's dry)."""
    h = np.asarray(heights, dtype=float)
    filled, lakes, rivers, flow, min_flow = find_water(h)
    surface = h - HIDDEN_DEPTH                                 # dry: hidden under the ground
    # bigger rivers are drawn deeper/wider: depth grows with log of the flow
    river_depth = RIVER_DEPTH * (1 + np.log2(np.maximum(flow / min_flow, 1)) / 3)
    surface = np.where(rivers, h + river_depth, surface)
    surface = np.where(lakes, filled, surface)                # lakes are flat at the spill level
    return surface, lakes, rivers


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

    def __init__(self, original_heights, scale):
        from ursina import color
        from TerrainHandler import FastTerrain

        surface, lakes, rivers = water_surface(original_heights)
        self.entity = FastTerrain(surface, scale=scale, texture=make_flow_texture(),
                                  texture_scale=(6, 6), color=color.white, double_sided=True)
        self.elapsed = 0.0
        self.job = None           # (thread, heights, key, result) while water is being worked out
        self.updates = 0          # how many times new water has been shown
        self.pending = None       # the newest request waiting for its turn
        self.depth = surface - np.asarray(original_heights, dtype=float)
        self.cache = {'original': (surface, 100 * lakes.mean(), 100 * rivers.mean())}   # O key is instant
        self.lake_percent = 100 * lakes.mean()
        self.river_percent = 100 * rivers.mean()
        print(f'Water: lakes {self.lake_percent:.1f}% of map, rivers {self.river_percent:.1f}%')

    CACHE_SIZE = 300          # remember the water for this many terrains (each is tiny)

    def request(self, heights, key=None):
        """Show the water for these heights, without making the app wait.

        Working out water takes 10-100 ms (more on big grids), so it's done in the
        background. Until it's ready, the previous water follows the new ground, then the
        new water appears. key names the terrain (e.g. 'original', or a step): water already
        worked out for the same key is reused straight away (O, Left/Right are instant).
        """
        h = np.asarray(heights, dtype=float)
        if key is not None and key in self.cache:
            self.pending = None
            self._show(h, *self.cache[key])
            return
        self.follow(h)
        self.pending = (h.copy(), key)        # only the newest request matters
        self._start_next()

    def _start_next(self):
        if self.job is not None or self.pending is None:
            return
        h, key = self.pending
        self.pending = None
        result = {}

        def work():
            result['water'] = water_surface(h)

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
            surface, lakes, rivers = result['water']
            entry = (surface, 100 * lakes.mean(), 100 * rivers.mean())
            if key is not None:
                if len(self.cache) >= self.CACHE_SIZE:
                    self.cache.pop(next(iter(self.cache)))      # forget the oldest one
                self.cache[key] = entry
            self._show(h, *entry)
        self._start_next()                    # a newer request came in meanwhile

    def _show(self, heights, surface, lake_percent, river_percent):
        self.updates += 1                     # shown on screen, to see the water keeping up
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