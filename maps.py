"""
maps.py - where the starting terrain comes from: a heightmap PNG, or a generated noise map.

Both give back heights as a NumPy array on the 0-255 scale (decimals allowed).
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom

import config
sigma = 2 # for smoothing the pngs by averaging the pixels around each point
try:
    from noise_map import create_heightmap      # the teammate's simplex-noise generator
    print('generated maps: noise_map.py')
except ImportError as problem:                  # the noise package isn't installed on this laptop
    create_heightmap = None
    print(f'generated maps: basic backup (noise_map.py needs the noise package: {problem})')

GENERATED = 'Generated (noise)'      # the name of the "make one" option in the menu


def map_names():
    """The options for the menu: every map in config.MAPS, then the generated one."""
    return list(config.MAPS) + [GENERATED]


def find_file(name):
    """Find a file by name in this folder or any folder inside it (e.g. maps/)."""
    if Path(name).exists():
        return Path(name)
    found = list(Path('.').glob('**/' + name))
    if not found:
        raise FileNotFoundError(f'cannot find {name} - check the name in config.MAPS')
    return found[0]


def load_heightmap(filename, size=None):
    """Read a heightmap PNG as heights, resized to size x size points (config.GRID_SIZE),
    whatever size the PNG is. (Same orientation as Ursina's Terrain.)"""
    size = size or config.GRID_SIZE
    img = Image.open(find_file(filename)).convert('L')     # greyscale: 0 = low, 255 = high
    if img.size != (size, size):
        img = img.resize([size, size], Image.LANCZOS)
    heights = np.asarray(img).astype(float)
    heights = np.swapaxes(np.flip(heights, axis=0), 0, 1)     # same orientation as Ursina uses
    return gaussian_filter(heights, sigma=sigma)      # smooth out the jagged edges of a PNG


def stand_in_noise(seed, size=64, octaves=5):
    """BASIC BACKUP generator: used only when noise_map.py (the main generator) can't run
    because the noise package isn't installed.
    How it works: a few grids of random numbers (3, 5, 9, 17, 33 points across), each
    smoothly stretched to the map size and added together, smaller grids counting less."""
    rng = np.random.default_rng(seed)
    h = np.zeros((size, size))
    for octave in range(octaves):
        cells = 2 ** (octave + 1) + 1                   # 3, 5, 9, 17, 33 random points across
        coarse = rng.random((cells, cells))
        h += zoom(coarse, size / cells, order=3)[:size, :size] / 2 ** octave   # smaller = weaker
    return h


def generate_heights(seed, res = 128, frequency=1.5, octaves=2):
    """A generated map, the same size as a loaded one (config.GRID_SIZE points across).

    The result is stretched so the lowest point is 0 and the highest is 255: then the
    "lowest point" and "highest point" typed in the menu really are the lowest and highest.
    """
    size = res
    if create_heightmap is not None:
        h = create_heightmap(seed, width=size, height=size, frequency=frequency,
                             octaves=octaves)
        h = np.swapaxes(np.flip(h, axis=0), 0, 1)      # same orientation as a loaded PNG
    else:
        h = stand_in_noise(seed, size, octaves)
    gaussian_filter(h, sigma=sigma, output=h)      # smooth out the jagged edges of a PNG
    h = h - h.min()
    return h / max(h.max(), 1e-9) * 255


def preview_image(heights):
    """Heights -> a greyscale picture (for the menu preview)."""
    picture = np.flip(np.swapaxes(heights, 0, 1), axis=0)      # undo the Ursina orientation
    return Image.fromarray(picture.clip(0, 255).astype(np.uint8))
