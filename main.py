from ursina import *
import procedural_noise as pn
app = Ursina(title='Math Hacks 2.0')

heightmap = "assets/generated_heightmap.png"
texture = "assets/Texture PNG.png"
pn.create_heightmap()
world = Entity(model=Terrain(heightmap= heightmap), scale = (35, 35, 35))
EditorCamera()      # drag with the mouse to orbit, scroll to zoom
app.run()
