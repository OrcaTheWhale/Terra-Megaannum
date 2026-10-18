"""
maps.py - where the starting terrain comes from: a heightmap PNG, or a generated noise map.

Both give back heights as a NumPy array on the 0-255 scale (decimals allowed).
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import zoom

import config

try:
    from noise_map import create_heightmap      # the teammate's simplex-noise generator
except ImportError as problem:                  # e.g. the 'noise' package isn't installed
    create_heightmap = None
    print(f'noise_map not available ({problem}) - generated maps use the simple stand-in')

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
    return np.swapaxes(np.flip(heights, axis=0), 0, 1)     # same orientation as Ursina uses


def stand_in_noise(seed, size=64, octaves=5):
    """Simple fractal noise: big smooth bumps + smaller bumps + even smaller bumps...
    Only used if noise_map.py can't be loaded (the 'noise' package needs installing)."""
    rng = np.random.default_rng(seed)
    h = np.zeros((size, size))
    for octave in range(octaves):
        cells = 2 ** (octave + 1) + 1                   # 3, 5, 9, 17, 33 random points across
        coarse = rng.random((cells, cells))
        h += zoom(coarse, size / cells, order=3)[:size, :size] / 2 ** octave   # smaller = weaker
    return h


def generate_heights(seed, frequency=1.5):
    """A generated map, the same size as a loaded one (config.GRID_SIZE points across).

    The result is stretched so the lowest point is 0 and the highest is 255: then the
    "lowest point" and "highest point" typed in the menu really are the lowest and highest.
    """
    size = config.GRID_SIZE
    if create_heightmap is not None:
        h = create_heightmap(seed, width=size, height=size, frequency=frequency)
        h = np.swapaxes(np.flip(h, axis=0), 0, 1)      # same orientation as a loaded PNG
    else:
        h = stand_in_noise(seed, size)
    h = h - h.min()
    return h / max(h.max(), 1e-9) * 255


def preview_image(heights):
    """Heights -> a greyscale picture (for the menu preview)."""
    picture = np.flip(np.swapaxes(heights, 0, 1), axis=0)      # undo the Ursina orientation
    return Image.fromarray(picture.clip(0, 255).astype(np.uint8))
