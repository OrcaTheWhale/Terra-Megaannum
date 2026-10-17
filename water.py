"""Stable valley rivers and conservative channel erosion for MathHacks."""


import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt, map_coordinates




def find_downhill(heights, diagonals=True):
    """Index of the lowest strictly lower adjacent cell, or -1 at a sink."""
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
    """Accumulate one unit of rainfall per cell, highest cells first."""
    h = np.asarray(heights, dtype=float)
    targets = np.asarray(downhill).ravel()
    flow = np.ones(h.size, dtype=float)
    for i in np.argsort(-h.ravel(), kind='stable'):
        j = targets[i]
        if j != -1:
            flow[j] += flow[i]
    return flow.reshape(h.shape)




def make_river_mask(heights, minimum_flow=90, flood_width=1.0,
                    mountain_limit=0.25, reference=None):
    """Narrow water channels following valleys, not a flat sea-level plane.


    reference is the original terrain, which stabilizes drainage as the
    displayed heights erode. The current heights still influence routing.
    """
    h = np.asarray(heights, dtype=float)
    guide = h if reference is None else 0.75 * reference + 0.25 * h
    guide = gaussian_filter(guide, sigma=1.3)
    downhill = find_downhill(guide)
    flow = flow_amount(guide, downhill)
    channel = flow >= minimum_flow
    if not np.any(channel):
        return channel, flow


    distance, nearest = distance_transform_edt(~channel, return_indices=True)
    nearest_height = guide[tuple(nearest)]
    nearest_flow = flow[tuple(nearest)]


    # Wider only around bigger rivers. Low banks can flood slightly.
    river_width = np.clip(
        1.12 + 0.25 * np.log2(np.maximum(nearest_flow / minimum_flow, 1.0)),
        1.12, 2.8
    ) * flood_width
    low_bank = guide <= nearest_height + 0.8
    wet = channel | ((distance <= river_width) & low_bank)


    mountains = guide >= np.percentile(guide, 70)
    flooded_high = np.flatnonzero(wet & mountains)
    allowed = int(np.count_nonzero(mountains) * mountain_limit)
    if len(flooded_high) > allowed:
        keep = flooded_high[np.argsort(guide.ravel()[flooded_high])[:allowed]]
        flat = wet.ravel()
        flat[flooded_high] = False
        flat[keep] = True
    return wet, flow




def erosion_profiles(flow, minimum_flow=90):
    """Build a river-bed incision profile and adjacent sediment-bank profile."""
    f = np.asarray(flow, dtype=float)
    channel = f >= minimum_flow
    amount = np.zeros_like(f)
    if not np.any(channel):
        return amount, amount.copy()


    amount[channel] = np.clip(
        0.30 + np.log2(f[channel] / minimum_flow) * 0.16,
        0.30, 1.0
    )
    bank = gaussian_filter(amount, sigma=1.3)
    bank[channel] = 0.0
    bank /= max(bank.sum(), 1e-12)
    return amount, bank




def carve_rivers(heights, incision, bank, strength=0.025):
    """Erode channels while redepositing ALL removed sediment onto banks.


    This stays stable because there is NO repeatedly-applied height sharpening,
    and erosion is limited by each cell's remaining elevation above zero.
    """
    h = np.asarray(heights, dtype=float)
    removed = np.minimum(strength * incision, np.maximum(h - 1.0, 0))
    if not np.any(removed):
        return h.copy()
    return h - removed + removed.sum() * bank




def make_water_mesh(heights, wet, vertical_scale=35):
    """Blue terrain-following water mesh aligned to FastTerrain's axes."""
    from ursina import Mesh


    surface = np.asarray(heights, dtype=float).T
    z, x = np.nonzero(np.asarray(wet, dtype=bool).T)
    if len(x) == 0:
        return Mesh(vertices=[], triangles=[], mode='triangle')


    # A small overlap connects neighbouring cells into continuous streams.
    corners_x = np.array([-0.51, 0.51, 0.51, -0.51])
    corners_z = np.array([-0.51, -0.51, 0.51, 0.51])
    xx = x[:, None] + corners_x
    zz = z[:, None] + corners_z
    y = map_coordinates(surface, [zz.ravel(), xx.ravel()], order=1,
                        mode='nearest')


    vertices = np.empty((x.size * 4, 3), dtype=np.float32)
    vertices[:, 0] = xx.ravel() / (surface.shape[1] - 1) - 0.5
    vertices[:, 1] = y / 255 + 0.035 / vertical_scale
    vertices[:, 2] = zz.ravel() / (surface.shape[0] - 1) - 0.5


    ids = np.arange(x.size * 4, dtype=np.uint32).reshape(-1, 4)
    triangles = ids[:, [0, 1, 2, 0, 2, 3]].ravel()
    uvs = np.tile(np.array([
        [0, 0], [1, 0], [1, 1], [0, 1]
    ], dtype=np.float32), (x.size, 1)).ravel()
    blue = np.array([28 / 255, 115 / 255, 185 / 255, 1], dtype=np.float32)
    colors = np.tile(blue, x.size * 4)
    return Mesh(vertices=vertices.ravel(), triangles=triangles,
                uvs=uvs, colors=colors, mode='triangle', static=False)



