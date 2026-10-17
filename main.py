from ursina import *
app = Ursina(title='Math Hacks 2.0')

heightmap = "Height Map PNG.png"
texture = "Texture PNG.png"
world = Entity(model=Terrain(heightmap= heightmap), texture = texture, scale = (35, 35, 35))
EditorCamera()      # drag with the mouse to orbit, scroll to zoom
app.run()
