import numpy as np
from noise import snoise2
from PIL import Image
height: int = 1000
width: int = 1000
seed: int = np.random.randint(1, 1000000) # random seed
frequency: float = 1.5 # higher values make more steeper and taller hills, while lower values make less smoother hills

value = np.zeros((height, width), dtype=np.uint8) #creates an array the size of the grid filled entirely with zeros, each entry as an 8 bit number for the greyscale values.
def create_heightmap():
    for y in range(height):
        for x in range(width):
            nx:float = (x / width - 0.5) * frequency
            ny:float = (y / height - 0.5) * frequency
            n = snoise2(nx, ny, octaves=4, persistence=0.5, lacunarity=2, base=seed) # creates a noise value from -1 to 1
            value[y, x] = int(np.clip((n+1)*127.5, 0,255)) # sets the pixel on the grid to an 8 bit greyscale value based off the the noise
    Image.fromarray(value, mode="L").save("assets/generated_heightmap.png") # creates greyscale heightmap using 8 bit greyscale values.
    