"""
noise_map.py - generates a heightmap from simplex noise (teammate's generator).

The maths is unchanged from the original script; it's now a function so the menu can
call it with a seed, size and frequency, and it gives back the heights directly.
Run this file on its own to save a heightmap PNG like before:  python noise_map.py
"""

import numpy as np
from noise import snoise2
from PIL import Image


def create_heightmap(seed, width=1000, height=1000, frequency=1.5):
    """A grid of heights from 0 to 255.

    seed       which map you get (same seed = same map)
    frequency  higher values make more steeper and taller hills, while lower values
               make less smoother hills

    The noise is smooth and continuous, so a small grid (e.g. 64 x 64) shows the same
    landscape as a big one, just with less detail - and is much faster to make.
    """
    value = np.zeros((height, width))   # decimals instead of whole numbers, so nothing is rounded off
    for y in range(height):
        for x in range(width):
            nx = (x / width - 0.5) * frequency
            ny = (y / height - 0.5) * frequency
            n = snoise2(nx, ny, octaves=4, persistence=0.5, lacunarity=2, base=seed)  # -1 to 1
            value[y, x] = np.clip((n + 1) * 127.5, 0, 255)                          # 0 to 255
    return value


if __name__ == '__main__':
    seed = np.random.randint(1, 1000000)    # random seed
    value = create_heightmap(seed)
    Image.fromarray(value.astype(np.uint8), mode='L').save('generated_heightmap.png')
    print(f'saved generated_heightmap.png (seed {seed})')
