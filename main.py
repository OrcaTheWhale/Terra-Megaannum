
"""MathHacks: stable, sharply defined river valleys with conserved soil."""
import os
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from ursina import *
from ursina.shaders import unlit_shader
from TerrainHandler import FastTerrain
from water import (
    make_river_mask, erosion_profiles, carve_rivers,
    make_water_mesh, make_flow_texture,
)

app = Ursina(title='Math Hacks 2.0 | Stable Rivers', development_mode=False)

HEIGHTMAP = 'Height Map PNG.png'
TEXTURE = 'Texture PNG.png'
SKIP = 4
SCALE = (35, 35, 35)

# Safe parameters: never apply sharpening on every frame.
MIN_RIVER_FLOW = 50            # Higher means fewer tributaries
FLOOD_WIDTH = 0.8              # Keep water confined to the channels
MAX_MOUNTAIN_FLOOD = 0.05      # Limit wet area in the highest terrain
CREEP_RATE = 0.006             # Small, mass-conserving soil creep per step
EROSION_PER_STEP = 0.025       # Gradual river incision, in heightmap units
INITIAL_CHANNEL_DEPTH = 20.0   # Initial visible channels, applied ONCE
RIVER_UPDATE_SECONDS = 2.0
FLOW_ANIMATION_SPEED = 0.12

start = Terrain(heightmap=HEIGHTMAP, skip=SKIP)
original = start.height_values.astype(float)
heights = original.copy()

# Gentle relief boost only at initialization (NOT inside update()).
def enhance_once(h):
    return h + 0.25 * (h - gaussian_filter(h, sigma=1.1))

# Pairwise, symmetric exchanges preserve total soil exactly.
def soil_creep(h, rate=CREEP_RATE):
    result = h.copy()
    difference_x = h[:, 1:] - h[:, :-1]
    difference_z = h[1:, :] - h[:-1, :]
    result[:, :-1] += rate * difference_x
    result[:, 1:] -= rate * difference_x
    result[:-1, :] += rate * difference_z
    result[1:, :] -= rate * difference_z
    return result

river_mask = None
river_flow = None
incision = None
bank = None

def river_data():
    global river_mask, river_flow, incision, bank
    river_mask, river_flow = make_river_mask(
        heights, minimum_flow=MIN_RIVER_FLOW,
        flood_width=FLOOD_WIDTH, mountain_limit=MAX_MOUNTAIN_FLOOD,
        reference=original
    )
    incision, bank = erosion_profiles(river_flow, MIN_RIVER_FLOW)

def reset_heights():
    global heights
    heights = enhance_once(original.copy())
    river_data()
    heights = carve_rivers(heights, incision, bank, INITIAL_CHANNEL_DEPTH)
    river_data()

reset_heights()

world = FastTerrain(heights, texture=TEXTURE, scale=SCALE, double_sided=True)
ghost = FastTerrain(original, scale=SCALE, wireframe=True,
                    color=color.rgba(255, 255, 255, 90), enabled=False)
river_water = Entity(scale=SCALE, color=color.white, texture=make_flow_texture(),
                     shader=unlit_shader, double_sided=True)

running = False
showing_original = False
water_visible = True
steps_per_frame = 100
redraw_timer = 0.0
river_timer = 0.0
hud_timer = 0.0
flow_offset = 0.0

camera.position = (0, 0, -110)
orbit = EditorCamera()
orbit.smoothing_helper.rotation_x = 50
info = Text(position=window.top_left + Vec2(0.02, -0.02), scale=0.8)


def update_water():
    river_data()
    river_water.model = make_water_mesh(heights, river_mask, SCALE[1])
    river_water.enabled = water_visible and not showing_original


def redraw():
    if not showing_original:
        world.set_heights(heights)


def save_change_map():
    change = heights - original
    limit = max(np.abs(change).max(), 1)
    fig, ax = plt.subplots()
    image = ax.imshow(change, cmap='RdBu', vmin=-limit, vmax=limit)
    fig.colorbar(image, ax=ax, label='height change')
    ax.set_title('Red = soil lost, blue = soil gained')
    fig.savefig('change_map.png', bbox_inches='tight', dpi=160)
    plt.close(fig)
    print('saved change_map.png')


def save_rivers_map():
    update_water()
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(heights.T, cmap='terrain', origin='lower')
    water = np.ma.masked_where(~river_mask.T, river_mask.T)
    ax.imshow(water, cmap='Blues', vmin=0, vmax=1, alpha=0.95, origin='lower',
              interpolation='nearest')
    ax.set_title('Narrow rivers and valley channels')
    fig.savefig('rivers.png', bbox_inches='tight', dpi=160)
    plt.close(fig)
    print('saved rivers.png')


def input(key):
    global running, showing_original, water_visible, steps_per_frame, FLOOD_WIDTH
    global redraw_timer, river_timer
    if key == 'space':
        running = not running
    elif key == 'o':
        showing_original = True
        world.set_heights(original)
        river_water.enabled = False
    elif key == 'o up':
        showing_original = False
        redraw()
        river_water.enabled = water_visible
    elif key == 'g':
        ghost.enabled = not ghost.enabled
    elif key == 'v':
        water_visible = not water_visible
        river_water.enabled = water_visible and not showing_original
    elif key == 'm':
        save_change_map()
    elif key == 'r':
        save_rivers_map()
    elif key == 'j':
        FLOOD_WIDTH = max(0.6, round(FLOOD_WIDTH - 0.1, 2))
        update_water()
    elif key == 'k':
        FLOOD_WIDTH = min(1.8, round(FLOOD_WIDTH + 0.1, 2))
        update_water()
    elif key == 'x':
        reset_heights()
        redraw()
        update_water()
        redraw_timer = river_timer = 0.0
    elif key in ('1', '2', '3'):
        steps_per_frame = {'1': 1, '2': 5, '3': 20}[key]


def update():
    global heights, redraw_timer, hud_timer, river_timer, flow_offset
    if running:
        if water_visible and not showing_original:
            flow_offset = (flow_offset + time.dt * FLOW_ANIMATION_SPEED) % 1.0
            river_water.texture_offset = Vec2(flow_offset, 0)
        for _ in range(steps_per_frame):
            heights = soil_creep(heights)
            heights = carve_rivers(heights, incision, bank, EROSION_PER_STEP)
        redraw_timer += time.dt
        river_timer += time.dt
        if redraw_timer >= 0.1:
            redraw()
            redraw_timer = 0.0
        if river_timer >= RIVER_UPDATE_SECONDS:
            update_water()
            river_timer = 0.0

    hud_timer += time.dt
    if hud_timer >= 0.3:
        hud_timer = 0.0
        moved = np.maximum(original - heights, 0).sum()
        coverage = 0 if river_mask is None else river_mask.mean() * 100
        max_flow = 0 if river_flow is None else river_flow.max()
        info.text = (
            f"{'RUNNING' if running else 'PAUSED'} | speed {steps_per_frame}"
            f"{' | SHOWING ORIGINAL' if showing_original else ''}\n"
            'Space pause | Hold O original | G ghost | X reset\n'
            'M change map | R river map | V water on/off | 1/2/3 speed\n'
            f'J narrower | K wider | Width {FLOOD_WIDTH:.2f} | Wet {coverage:.1f}%\n'
            f'Soil total: {heights.sum():,.0f} (initial {original.sum():,.0f})\n'
            f'Soil moved: {moved:,.0f} | Flow max: {max_flow:,.0f}\n'
            f'High {heights.max():.1f} (was {original.max():.1f}) | '
            f'Low {heights.min():.1f} (was {original.min():.1f})\n'
            f'Roughness {heights.std():.2f} (was {original.std():.2f})'
        )


print('terrain:', heights.shape, 'original soil:', original.sum())
update_water()
app.run()
