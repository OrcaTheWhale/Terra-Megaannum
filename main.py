from ursina import *

app = Ursina()
Entity(model='cube', color=color.orange)
EditorCamera()      # drag with the mouse to orbit, scroll to zoom
app.run()