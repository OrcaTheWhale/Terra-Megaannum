"""
main.py - starts the app and runs the main loop. Run:  python main.py

Where things live:
    config.py        settings and numbers
    conditions.py    the physics (soil creep; add rain, wind... here)
    climate.py       seasons and temperature
    simulation.py    time, steps, history, looking back
    analysis.py      scores, likelihood, charts and maps
    ui.py            control panel and information text
    TerrainHandler.py  fast 3D drawing
"""

from ursina import *

import analysis
import climate
import config
from simulation import Simulation
from TerrainHandler import FastTerrain
from ui import ControlPanel, hud_text

app = Ursina(title='Math Hacks 2.0', development_mode=False)

# ---------------------------------------------------------------- load the terrain once
start = Terrain(heightmap=config.HEIGHTMAP, skip=config.SKIP)
original = start.height_values.astype(float)       # decimals, so small changes aren't lost
print("terrain size:", original.shape)
print("graphics:", base.win.gsg.driver_renderer)

sim = Simulation(original)

world = FastTerrain(original, texture=config.TEXTURE, scale=config.SCALE, double_sided=True)
ghost = FastTerrain(original, scale=config.SCALE, wireframe=True,
                    color=color.rgba(1, 1, 1, 0.35), enabled=False)

camera.position = (0, 0, -110)
orbit = EditorCamera()
orbit.smoothing_helper.rotation_x = 50
info = Text(position=window.top_left + Vec2(0.02, -0.02))

# ---------------------------------------------------------------- state
running = False
view_step = None             # None = showing the latest step; a number = looking back
showing_original = False
steps_per_frame = 1
redraw_timer = 0
hud_timer = 0
likelihood_score = None
spread = None
runs_used = 0


def shown_step():
    return sim.step if view_step is None else view_step


def shown_heights():
    return sim.heights if view_step is None else sim.heights_at(view_step)


def show(h):
    world.set_heights(h)


# ---------------------------------------------------------------- actions
def toggle_running():
    global running, view_step, likelihood_score
    if running:
        running = False
        return
    if view_step is not None and view_step < sim.step:
        sim.rewind_to(view_step)          # continue from the step we're looking at
        print(f'continuing from step {sim.step}')
    view_step = None
    if sim.step >= panel.target:
        show(sim.heights)
        return                            # already reached the target
    likelihood_score = None               # the result is about to change
    running = True


def step_view(amount):
    global view_step, running
    running = False
    new_step = max(0, min(sim.step, shown_step() + amount))
    view_step = None if new_step == sim.step else new_step
    show(shown_heights())


def reset():
    global running, view_step, likelihood_score, spread
    sim.reset()
    running = False
    view_step = None
    likelihood_score = None
    spread = None
    show(sim.heights)


def check_likelihood():
    global likelihood_score, spread, runs_used
    if sim.step == 0:
        print('nothing simulated yet')
        return
    likelihood_score, spread, runs_used = analysis.likelihood(sim)


panel = ControlPanel(on_start_pause=toggle_running, on_reset=reset,
                     on_prev=lambda: step_view(-1), on_next=lambda: step_view(1),
                     on_likelihood=check_likelihood)


# ---------------------------------------------------------------- keys
def input(key):
    global showing_original, steps_per_frame
    if key == 'space':
        toggle_running()
    elif key == 'r':
        reset()
    elif key in ('left arrow', 'left arrow hold'):
        step_view(-1)
    elif key in ('right arrow', 'right arrow hold'):
        step_view(1)
    elif key == 'l':
        check_likelihood()
    elif key == 'o':
        showing_original = True
        show(original)
    elif key == 'o up':
        showing_original = False
        show(shown_heights())
    elif key == 'g':
        ghost.enabled = not ghost.enabled
    elif key == 'm':
        analysis.save_change_map(shown_heights(), original, f'Step {shown_step()}')
    elif key == 'c':
        analysis.save_history_chart(sim.history)
    elif key == 'u':
        analysis.save_uncertainty_map(spread, likelihood_score or 0)
    elif key in ('1', '2', '3'):
        steps_per_frame = {'1': 1, '2': 5, '3': 20}[key]


# ---------------------------------------------------------------- main loop
def update():
    global running, redraw_timer, hud_timer

    if running:
        for i in range(steps_per_frame):
            if sim.step >= panel.target:          # reached the chosen number of steps
                running = False
                check_likelihood()                # score the final result automatically
                break
            sim.advance(panel.step_days, panel.enabled())

        redraw_timer += time.dt
        if redraw_timer > 0.1 and not showing_original:
            show(sim.heights)
            redraw_timer = 0

    hud_timer += time.dt
    if hud_timer > 0.3:
        hud_timer = 0
        step = shown_step()
        h = shown_heights()
        land_changed, soil_moved = analysis.change_scores(h, original)
        sea_temp = sim.sea_temp_at(step)

        if running:
            status = 'RUNNING'
        elif view_step is not None:
            status = 'LOOKING BACK'
        elif sim.step >= panel.target:
            status = 'FINISHED'
        else:
            status = 'PAUSED'

        info.text = hud_text(
            status=status, step=step, latest_step=sim.step, target=panel.target,
            unit=panel.unit, days=sim.days_at(step), sea_temp=sea_temp,
            below_zero=climate.freezing_fraction(h, sea_temp) * 100,
            enabled=panel.enabled(),
            scores=(land_changed, soil_moved, h.sum(), h.std(), original.std()),
            likelihood=likelihood_score, runs=runs_used, speed=steps_per_frame,
            showing_original=showing_original)


app.run()