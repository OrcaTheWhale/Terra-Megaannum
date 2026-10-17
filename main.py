from ursina import *
import procedural_noise as pn
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from TerrainHandler import FastTerrain

#to do: add a frame stepper, to check what it would look like in 10days / 10 years / 100 years, and to go back and compare

# development_mode=False turns off Ursina's debug extras (hot reloading etc.), which saves time every frame
app = Ursina(title='Math Hacks 2.0', development_mode=False)

heightmap = "assets/generated_heightmap.png"
texture = "assets/Texture PNG.png"
skip = 4
scale = (35, 10, 35)

# load the PNG once, then convert to decimals for changes
start = Terrain(heightmap=heightmap, skip=skip)
heights = start.height_values.astype(float)
original = heights.copy()
print("terrain size:", heights.shape)
print("graphics:", base.win.gsg.driver_renderer)     # which GPU Ursina is drawing with

# FastTerrain: rebuilding the Terrain much faster
def generate_world():
    pn.create_heightmap()
    world = FastTerrain(heights, texture=texture, scale=scale, double_sided=True)
generate_world()

ghost = FastTerrain(original, scale=scale, wireframe=True,
                    color=color.rgba(1, 1, 1, 0.35), enabled=False)

camera.position = (0, 0, -110)
orbit = EditorCamera()
orbit.smoothing_helper.rotation_x = 50
info = Text(position=window.top_left + Vec2(0.02, -0.02))


#Rebuilding
def redraw():
    world.set_heights(heights)


#averages all the heights of nearest soil, and ensures no soil gets removed or lost
def soil_creep(h, rate=0.2):
    #make sure the edges have neighbours, then compare each
    p = np.pad(h, 1, mode='edge')      
    up    = p[:-2, 1:-1]               # every point's neighbour above
    down  = p[2:,  1:-1]               # ...below
    left  = p[1:-1, :-2]               # ...left
    right = p[1:-1, 2:]                # ...right
    #get average of height
    average = (up + down + left + right) / 4
    #new height to send to redraw
    return h + rate * (average - h)


#saving the map to compare differences
def save_change_map():
    #showing the change in red = lost, blue = gain
    change = heights - original
    #avoid divide by 0
    biggest = abs(change).max() or 1   
    plt.imshow(change, cmap='RdBu', vmin=-biggest, vmax=biggest)
    plt.colorbar(label='height change')
    plt.title('Red = soil lost, blue = soil gained')
    plt.savefig('change_map.png')
    plt.close()
    print('saved change_map.png')


running = False
showing_original = False
steps_per_frame = 1
redraw_timer = 0
hud_timer = 0


def input(key):
    global running, showing_original, steps_per_frame
    if key == 'space':
        running = not running
    elif key == 'o':
        showing_original = True
        world.set_heights(original)
    elif key == 'o up':
        showing_original = False
        redraw()
    elif key == 'g':
        ghost.enabled = not ghost.enabled
    elif key == 'm':
        save_change_map()
    elif key == '1':
        steps_per_frame = 1
    elif key == '2':
        steps_per_frame = 5
    elif key == '3':
        steps_per_frame = 20



def update():
    global heights, redraw_timer, hud_timer
    if running:
        for i in range(steps_per_frame):
            heights = soil_creep(heights)

        #rebuild
        redraw_timer += time.dt
        if redraw_timer > 0.1 and not showing_original:
            redraw()
            redraw_timer = 0

    hud_timer += time.dt
    if hud_timer > 0.3:
        hud_timer = 0
        #counting the total soil that moved off of high spots
        lost = (original - heights).clip(min=0).sum()

        info.text = (
            f"{'RUNNING' if running else 'PAUSED'}   speed {steps_per_frame}"
            f"{'   SHOWING ORIGINAL' if showing_original else ''}\n"
            f"Space start/pause | hold O original | G ghost | M change map | 1 2 3 speed\n"
            f"Total soil:    {heights.sum():,.0f}  (should never change)\n"
            f"Soil moved:    {lost:,.0f}\n"
            f"Highest point: {heights.max():.1f}   (was {original.max():.1f})\n"
            f"Lowest point:  {heights.min():.1f}   (was {original.min():.1f})\n"
            f"Roughness:     {heights.std():.2f}   (was {original.std():.2f})")


app.run()