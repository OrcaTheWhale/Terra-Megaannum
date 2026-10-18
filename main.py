"""
main.py - starts the app and runs the main loop. Run:  python main.py

Where things live:
    config.py        settings and numbers
    conditions.py    the physics (soil creep; add rain, wind... here)
    climate.py       seasons and temperature
    simulation.py    time, steps, history, looking back
    analysis.py      scores, likelihood, charts and maps
    ui.py            control panel and information text
    water.py         rivers and lakes (where the rain goes), drawn on top of the terrain
    menu.py          the main menu (choose a map, describe the place)
    maps.py          loading heightmap PNGs and generating noise maps
    TerrainHandler.py  fast 3D drawing
    terrain_shader.py  grass / rock / snow colouring on the graphics card
"""

from ursina import *

import analysis
import climate
import config
from menu import MainMenu
from sensors import SensorReader
from simulation import Simulation
from TerrainHandler import FastTerrain
from procedural_noise import create_heightmap
from terrain_shader import terrain_shader
from ui import ControlPanel, hud_text
from water import RiverSystem

app = Ursina(title=f'Math Hacks 2.0 - World in a Box {config.VERSION}', development_mode=False)
print('World in a Box', config.VERSION)
print("graphics:", base.win.gsg.driver_renderer)

sensors = SensorReader(config.SENSOR_PORT)     # reads the ESP32 in the background
sensors.start()

info = Text(position=window.top_left + Vec2(0.02, -0.02))
busy_text = Text('', origin=(0, 0), y=-0.43, scale=1.3, enabled=False)   # "Calculating likelihood..."
show_fps = False             # F key: frames per second in the top line of the text
fps_line = ''
fps_frames, fps_timer, slowest_frame = 0, 0.0, 0.0

# These are made by start_world() once a map is chosen in the menu. Until then they're None.
original = None
sim = None
world = None
ghost = None
rivers = None
panel = None

# ---------------------------------------------------------------- state
running = False
view_step = None             # None = showing the latest step; a number = looking back
showing_original = False
speed = config.DEFAULT_SPEED  # key in config.RUN_SPEEDS: how many seconds a whole run takes to watch
step_credit = 0.0            # steps owed so far this run (fractions carry over between frames)
run_goal = None              # the step number the current run stops at (None = no run going)
redraw_timer = 0
water_timer = 0
hud_timer = 0
likelihood_score = None
spread = None
runs_used = 0
manual_warming = 0.0         # Up/Down keys add or remove warming by hand (works without sensors)
likelihood_job = None        # the likelihood calculation running in the background, if any


def shown_step():
    return sim.step if view_step is None else view_step


def shown_heights():
    return sim.heights if view_step is None else sim.heights_at(view_step)


def show(h, water=True, key=None):
    """Draw these heights. key names them for the water cache: 'original' or a step number.
    water=False: don't work the water out again, just move it with the ground (cheap)."""
    world.set_heights(h)
    if not rivers.enabled:
        return
    if water:                      # the water is worked out (in the background) for this terrain
        rivers.request(h, key if key == 'original' else (sim.timeline, key))
    else:
        rivers.follow(h)


def show_step(step):
    show(sim.heights_at(step) if step != sim.step else sim.heights, key=step)


# ---------------------------------------------------------------- actions
def stop_likelihood():
    """Throw away a likelihood calculation that's still running."""
    global likelihood_job
    if likelihood_job is not None:
        likelihood_job.cancel()
        likelihood_job = None
    busy_text.enabled = False


def toggle_running():
    """Start adds the number of steps in the box (of the chosen length) to wherever you are.
    So: 365 Day steps, then 2 Season steps, then 100 x 1,000 yr... all in one timeline.
    Pressing it during a run pauses; pressing again carries on to the same goal."""
    global running, view_step, likelihood_score, run_goal
    panel.steps_field.active = False      # stop typing in the steps box
    if running:
        running = False
        show_step(sim.step)               # paused: work the water out properly
        return
    if view_step is not None and view_step < sim.step:
        sim.rewind_to(view_step)          # continue from the step we're looking at
        run_goal = None
        print(f'continuing from step {sim.step}')
    view_step = None
    if run_goal is None or sim.step >= run_goal:          # a new run
        if sim.step >= config.MAX_STEPS:
            print(f'reached the limit of {config.MAX_STEPS} steps - press R to reset, '
                  f'or use longer steps')
            return
        run_goal = min(sim.step + panel.steps, config.MAX_STEPS)
    likelihood_score = None               # the result is about to change
    stop_likelihood()
    running = True


def step_view(amount):
    global view_step, running
    running = False
    new_step = max(0, min(sim.step, shown_step() + amount))
    view_step = None if new_step == sim.step else new_step
    show_step(new_step)


def reset():
    global running, view_step, likelihood_score, spread, run_goal
    stop_likelihood()
    sim.reset()
    running = False
    run_goal = None
    view_step = None
    likelihood_score = None
    spread = None
    show(sim.heights)


def check_likelihood():
    """Start calculating the likelihood score in the background."""
    global likelihood_job, likelihood_score
    if sim.step == 0:
        print('nothing simulated yet')
        return
    stop_likelihood()
    likelihood_score = None
    likelihood_job = analysis.LikelihoodJob(sim)
    busy_text.enabled = True


def collect_likelihood():
    """Each frame: show progress, and pick up the result once it's ready."""
    global likelihood_job, likelihood_score, spread, runs_used
    if likelihood_job is None:
        return
    if likelihood_job.version != sim.version:      # the terrain changed since it started
        stop_likelihood()
        return
    if likelihood_job.finished:
        likelihood_score, spread, runs_used = likelihood_job.result
        likelihood_job = None
        busy_text.enabled = False
    else:
        done, total = likelihood_job.done_runs, likelihood_job.total_runs
        busy_text.text = f'Calculating likelihood... {done}/{total} runs'


# ---------------------------------------------------------------- starting from the menu
def make_world(heights, texture):
    """The terrain: the map's own texture, or grass/rock/snow blended by terrain_shader."""
    if texture and config.TERRAIN_LOOK == 'texture':
        return FastTerrain(heights, texture=texture, scale=config.SCALE, double_sided=True)

    textures = {name: load_texture(path) for name, path in config.TERRAIN_TEXTURES.items()}
    missing = [config.TERRAIN_TEXTURES[name] for name, tex in textures.items() if tex is None]
    if missing:                       # e.g. the textures folder isn't there: plain colour + lighting
        print('textures not found, using a plain colour:', missing)
        from ursina.shaders import basic_lighting_shader
        return FastTerrain(heights, color=color.rgb(*config.GENERATED_COLOR),
                           shader=basic_lighting_shader, scale=config.SCALE, double_sided=True)

    terrain = FastTerrain(heights, scale=config.SCALE, double_sided=True, shader=terrain_shader)
    for name, tex in textures.items():
        tex.filtering = 'mipmap'      # pre-shrunk copies for distant slopes: faster, and no shimmering
        terrain.set_shader_input(name, tex)
    terrain.set_shader_input('snow_line', 2.0)          # no snow until the climate sets it
    real_height = config.MAX_ELEVATION_M - config.MIN_ELEVATION_M
    terrain.set_shader_input('height_ratio', real_height / config.MAP_WIDTH_M)
    return terrain


def live_sea_temp(step):
    """Sea-level temperature for the step being shown.

    Looking back at an earlier step: the temperature that was recorded when that step ran
    (including any sensor warming at the time), so you see the past climate as it was.
    At the latest step: worked out with the sensor's warming right now, so heating the
    sensor melts the snow straight away, even while paused.
    """
    if 0 < step < sim.step:           # looking back: what it really was back then
        return sim.steps[step - 1]['sea_temp']
    if step == 0:                     # before the first step: the climate over one step of the chosen length
        return climate.sea_level_temp(0, panel.step_days)
    s = sim.steps[step - 1]
    return climate.sea_level_temp(s['start_day'], s['dt_days'])


def start_world(heights, texture, settings):
    """Called by the menu's START button: build the terrain, simulation and control panel."""
    global original, sim, world, ghost, rivers, panel

    for name, value in settings.items():      # the numbers typed in the menu replace config.py's
        setattr(config, name, value)

    original = heights                        # decimals, so small changes aren't lost
    # every step keeps a copy of the terrain for looking back: limit the steps to fit in memory
    bytes_per_step = original.size * 4
    config.MAX_STEPS = min(config.MAX_STEPS, int(config.SNAPSHOT_MEMORY_MB * 1e6 / bytes_per_step))
    print("terrain size:", original.shape, "| settings:", settings)
    sim = Simulation(original)

    world = make_world(original, texture)
    ghost = FastTerrain(original, scale=config.SCALE, wireframe=True,
                        color=color.rgba(1, 1, 1, 0.35), enabled=False)
    rivers = RiverSystem(original, scale=config.SCALE)    # water.py owns all river behaviour

    camera.position = (0, 0, -110)
    orbit = EditorCamera()
    orbit.smoothing_helper.rotation_x = 50

    panel = ControlPanel(on_start_pause=toggle_running, on_reset=reset,
                         on_prev=lambda: step_view(-1), on_next=lambda: step_view(1),
                         on_likelihood=check_likelihood)


menu = MainMenu(on_start=start_world)


# ---------------------------------------------------------------- keys
def input(key):
    global showing_original, speed, manual_warming, show_fps
    if sim is None:
        return          # still in the menu
    if panel.typing():  # typing a number in the steps box: shortcut keys are ignored...
        if key in ('enter', 'escape', 'tab'):
            panel.steps_field.active = False   # ...until Enter (or a click elsewhere)
        return
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
        show(original, key='original')
    elif key == 'o up':
        showing_original = False
        show_step(shown_step())
    elif key == 'g':
        ghost.enabled = not ghost.enabled
    elif key == 'w':
        rivers.enabled = not rivers.enabled
        if rivers.enabled:
            show_step(shown_step())                # catch up: it isn't recalculated while hidden
    elif key == 'm':
        analysis.save_change_map(shown_heights(), original, f'Step {shown_step()}')
    elif key == 'c':
        analysis.save_history_chart(sim.history)
    elif key == 'u':
        analysis.save_uncertainty_map(spread, likelihood_score or 0)
    elif key in config.RUN_SPEEDS:
        speed = key
    elif key in ('up arrow', 'up arrow hold'):
        manual_warming += 0.5
    elif key in ('down arrow', 'down arrow hold'):
        manual_warming -= 0.5
    elif key == 'z':
        sensors.rezero()
    elif key == 'f':
        show_fps = not show_fps


def sensor_lines():
    """Two lines of text describing the sensors and the climate change they cause."""
    if sensors.connected():
        strength, direction = sensors.wind()
        wind = f'{strength:.2f}' + (f' toward {direction:.0f} deg' if direction is not None else '')
        readings = (f"Sensors ({sensors.port}): temp {sensors.get('temp'):.1f} C | "
                    f"rain {sensors.norm('hum'):.2f} | sun {sensors.norm('light'):.2f} | "
                    f"fire {sensors.norm('flame'):.2f} | wind {wind}")
    else:
        readings = f"Sensors: not connected ({sensors.error or 'connecting...'})"
    sea_temp = live_sea_temp(shown_step())
    freezing_m = sea_temp / climate.LAPSE_RATE
    climate_line = (f"Climate: {climate.warming_c:+.1f} C vs normal "
                    f"(sensor {sensors.temp_change():+.1f}, keys {manual_warming:+.1f})   "
                    f"Snow line: {freezing_m:,.0f} m")
    water_line = (f"Water: lakes {rivers.lake_percent:.1f}% of map, rivers {rivers.river_percent:.1f}%"
                  f"   worked out {rivers.updates} times{' (working...)' if rivers.job else ''}"
                  f"   (W show/hide)")
    return readings + '\n' + climate_line + '\n' + water_line


# ---------------------------------------------------------------- main loop
def finish_run():
    """Reached the target: draw the final terrain and water, then score it."""
    global running, step_credit, run_goal
    running = False
    step_credit = 0
    run_goal = None
    show_step(sim.step)
    if config.AUTO_LIKELIHOOD:
        check_likelihood()                # score the final result automatically


def measure_fps():
    """Frames per second and the slowest frame in the last half second (F to show)."""
    global fps_frames, fps_timer, slowest_frame, fps_line
    fps_frames += 1
    fps_timer += time.dt
    slowest_frame = max(slowest_frame, time.dt)
    if fps_timer >= 0.5:
        fps_line = (f'{fps_frames / fps_timer:.0f} FPS, slowest frame {slowest_frame * 1000:.0f} ms, '
                    f'{original.shape[0]} x {original.shape[1]} points')
        fps_frames, fps_timer, slowest_frame = 0, 0.0, 0.0


def update():
    global running, redraw_timer, water_timer, hud_timer, step_credit

    if sim is None:                       # still in the menu
        return
    measure_fps()

    # the sensor's temperature change (plus the Up/Down keys) shifts the whole climate
    climate.warming_c = sensors.temp_change() + manual_warming
    collect_likelihood()
    rivers.update(time.dt)

    if running:
        # Steps per second are set so the whole run takes RUN_SPEEDS[speed] seconds to watch,
        # whether it's 10 steps or 1000. (Before, it was 1 step per frame, so a 1000-step run
        # took ~17 s at 60 fps even though each step only takes a fraction of a millisecond.)
        step_credit += panel.steps / config.RUN_SPEEDS[speed] * time.dt
        frame_start = time.perf_counter()
        while step_credit >= 1 and sim.step < run_goal:
            sim.advance(panel.step_days, panel.enabled())
            step_credit -= 1
            if time.perf_counter() - frame_start > 0.02:   # never spend more than 20 ms per frame
                break
        if sim.step >= run_goal:              # added all the steps asked for
            finish_run()

    if running and not showing_original:
        # redraw the terrain 10 times a second. The water is worked out again in the background
        # every WATER_REDRAW_SECONDS (0 = only when the run pauses or ends); in between, the
        # last water follows the ground
        redraw_timer += time.dt
        water_timer += time.dt
        if redraw_timer > 0.1:
            every = config.WATER_REDRAW_SECONDS
            update_water = every > 0 and water_timer > every
            show(sim.heights, water=update_water, key=sim.step)
            redraw_timer = 0
            if update_water:
                water_timer = 0

    hud_timer += time.dt
    if hud_timer > 0.3:
        hud_timer = 0
        panel.refresh()
        step = shown_step()
        h = shown_heights()
        land_changed, soil_moved = analysis.change_scores(h, original)
        sea_temp = live_sea_temp(step)
        world.set_shader_input('snow_line', climate.snow_line(sea_temp))   # snow follows the climate

        if running:
            status = 'RUNNING'
        elif view_step is not None:
            status = 'LOOKING BACK'
        elif run_goal is None:
            status = 'READY'
        else:
            status = 'PAUSED'

        info.text = hud_text(
            status=status, step=step, latest_step=sim.step,
            target=f' / {run_goal}' if run_goal is not None else '',
            unit=panel.unit, days=sim.days_at(step), sea_temp=sea_temp,
            below_zero=climate.freezing_fraction(h, sea_temp) * 100,
            enabled=panel.enabled(),
            scores=(land_changed, soil_moved, h.sum(), h.std(), original.std()),
            likelihood=likelihood_score, runs=runs_used,
            speed=f'{config.RUN_SPEEDS[speed]:g} s per run (keys 1 2 3)'
                  + (f'   |   {fps_line}' if show_fps else f'   |   {config.VERSION}'),
            showing_original=showing_original, sensor_lines=sensor_lines(),
            likelihood_progress=None if likelihood_job is None
            else (likelihood_job.done_runs, likelihood_job.total_runs))

app.run()
