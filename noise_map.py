"""noise_map.py - generates a heightmap from simplex noise (teammate's generator).
Needs the noise package. Run on its own to save a PNG: python noise_map.py
"""

import numpy as np
from noise import snoise2
from PIL import Image


def create_heightmap(seed, width=1000, height=1000, frequency=1.5, octaves=2):
    """A grid of heights from 0 to 255."""
    value = np.zeros((height, width))   # decimals instead of whole numbers, so nothing is rounded off
    for y in range(height):
        for x in range(width):
            nx = (x / width - 0.5) * frequency
            ny = (y / height - 0.5) * frequency
            n = snoise2(nx, ny, octaves=octaves, persistence=0.5, lacunarity=2, base=seed)
            value[y, x] = np.clip((n + 1) * 127.5, 0, 255)                          # 0 to 255
    return value


if __name__ == '__main__':
    seed = np.random.randint(1, 1000000)    # random seed
    value = create_heightmap(seed)
    Image.fromarray(value.astype(np.uint8), mode='L').save('generated_heightmap.png')
    print(f'saved generated_heightmap.png (seed {seed})')
