"""main.py - starts the app and runs the main loop. Run: python main.py

The physics lives in conditions.py, erosion.py, vegetation.py, water.py, rain.py and
climate.py; simulation.py keeps the history; ui.py, menu.py and weather.py are the screen.
"""

from ursina import *

import analysis
import climate
import config
from menu import MainMenu
import sensors as sensors_module
from sensors import SensorReader
from simulation import Simulation
from TerrainHandler import FastTerrain
from terrain_shader import terrain_shader
from ui import ControlPanel, hud_text
from water import RiverSystem
from weather import Weather
import vegetation
import rain
import numpy as np
from PIL import Image

app = Ursina(title=f'Math Hacks 2.0 - Terra Megaannum {config.VERSION}', development_mode=False, icon="assets/Terra-Megaannum.ico")
print('Terra Megaannum', config.VERSION)
Sky()
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
weather = None
panel = None

# ---------------------------------------------------------------- state
running = False
view_step = None             # None = showing the latest step; a number = looking back
showing_original = False
speed = config.DEFAULT_SPEED  # key in config.RUN_SPEEDS: how many seconds a whole run takes to watch
step_credit = 0.0            # steps owed so far this run (fractions carry over between frames)
run_goal = None              # the step number the current run stops at (None = no run going)
nonstop = False              # 0 in the steps box: run until paused (continuous mode)
run_box = None               # what the steps box said when the current run started
redraw_timer = 0
water_timer = 0
hud_timer = 0
likelihood_score = None
spread = None
runs_used = 0
manual_warming = 0.0         # Up/Down keys add or remove warming by hand (works without sensors)
manual_rain = 0.0            # [ and ] keys add or remove yearly rain by hand (mm)
last_water_climate = None    # the climate the water was last worked out for
veg_shown = None             # which plant map the terrain is showing (so it's only redrawn on change)
fires = 0                    # goes up each time fire burns plants (to redraw the plant map)
likelihood_job = None        # the likelihood calculation running in the background, if any
manual_wind = config.WIND_STRENGTH       # Y key cycles the wind strength (when there's no joystick)
manual_wind_toward = config.WIND_TOWARD_DEG   # J / K keys turn the wind (when the joystick gives no direction)
orbit = None                 # the camera controller (EditorCamera)
auto_orbit = False           # X key: the camera circles the map slowly by itself
panel_widgets = []           # the control panel's buttons and text (H hides them)
ui_hidden = False            # H key: hide all text and buttons, for a clean view of the map


def shown_step():
    return sim.step if view_step is None else view_step


def shown_heights():
    return sim.heights if view_step is None else sim.heights_at(view_step)


def rain_mm():
    """Yearly rain (mm): from the menu, scaled by the humidity sensor, plus the [ ] keys."""
    rain = config.ANNUAL_RAIN_MM
    if sensors.has('hum'):
        rain *= sensors.rain_factor()   # humidity vs the zero point: drier 0.25x ... breathed on 3x
    return max(0.0, rain + manual_rain)


def current_wind():
    """(strength 0-1, direction it blows TOWARD in degrees): the joystick if connected, else the keys."""
    if sensors.has('tilt'):
        strength, direction = sensors.wind()
        return strength, (manual_wind_toward if direction is None else direction)
    return manual_wind, manual_wind_toward


def water_climate():
    """What the lakes depend on: (yearly rain, yearly mean sea-level temperature, wind strength,
    wind direction), rounded so tiny sensor wobbles don't make the water recalculate all the time."""
    strength, toward = current_wind()
    return (round(rain_mm(), -1), round(config.AVG_TEMP_C + climate.warming_c, 1),
            round(strength, 1), round(toward / 15) * 15 % 360)


def rain_here(h):
    """Yearly rain at every point of these heights: wind-driven rain (rain.py)."""
    strength, toward = current_wind()
    return rain.rain_map(h, sim.cell_m, rain_mm(), strength, toward)


def show(h, water=True, key=None):
    """Draw these heights. key names them for the water cache: 'original' or a step number.
    water=False: don't work the water out again, just move it with the ground (cheap)."""
    global last_water_climate
    world.set_heights(h)
    if not rivers.enabled:
        return
    if water:                      # the water is worked out (in the background) for this terrain
        last_water_climate = water_climate()
        rivers.request(h, key if key == 'original' else (sim.timeline, key), last_water_climate)
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
    """Start adds the number of steps in the box (of the chosen length) to wherever you are."""
    global running, view_step, likelihood_score, run_goal, nonstop, run_box
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
    if run_box != panel.steps_field.text:
        run_goal = None                   # the number in the box changed while paused: a new run
    if run_goal is None or sim.step >= run_goal:          # a new run
        if sim.step >= config.MAX_STEPS:
            print(f'reached the limit of {config.MAX_STEPS} steps - press R to reset, '
                  f'or use longer steps')
            return
        nonstop = panel.nonstop
        run_box = panel.steps_field.text
        # nonstop: keep going until paused, or until the memory for looking back is full
        run_goal = config.MAX_STEPS if nonstop else min(sim.step + panel.steps, config.MAX_STEPS)
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
    sensors.rezero()                      # fresh zero point for the sensors too
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
    if missing:
        # e.g. the textures folder was renamed: use plain colours instead, but keep the shader,
        # so snow, rock and plants still show. Fix the paths in config.TERRAIN_TEXTURES.
        print('\n*** TEXTURES NOT FOUND - using plain colours. Check TERRAIN_TEXTURES in config.py:')
        for path in missing:
            print('   ', path)
        plain = {'grass_tex': [c * 255 for c in config.GENERATED_COLOR],
                 'rock_tex': (120, 108, 96), 'snow_tex': (245, 248, 252),
                 'dirt_tex': (125, 100, 72)}
        for name in textures:
            if textures[name] is None:
                textures[name] = Texture(Image.new('RGB', (4, 4), tuple(int(v) for v in plain[name])))

    terrain = FastTerrain(heights, scale=config.SCALE, double_sided=True, shader=terrain_shader)
    for name, tex in textures.items():
        tex.filtering = 'mipmap'      # pre-shrunk copies for distant slopes: faster, and no shimmering
        terrain.set_shader_input(name, tex)
    terrain.set_shader_input('snow_line', 2.0)          # no snow until the climate sets it
    terrain.set_shader_input('veg_on', 0.0)             # plant map arrives once vegetation runs
    terrain.set_shader_input('veg_tex', Texture(Image.new('L', (4, 4), 255)))
    real_height = config.MAX_ELEVATION_M - config.MIN_ELEVATION_M
    terrain.set_shader_input('height_ratio', real_height / config.MAP_WIDTH_M)
    return terrain


def mean_temp():
    """Yearly mean sea-level temperature now (plants respond to the yearly climate)."""
    return config.AVG_TEMP_C + climate.warming_c


def update_vegetation():
    """Start the plant map if needed, burn plants where there's a fire, and show the plant map."""
    global veg_shown, fires
    if 'Vegetation' in panel.enabled() and sim.state.get('veg') is None and view_step is None:
        # before the first step: a mature landscape for today's climate
        sim.state['veg'] = vegetation.capacity(sim.heights, sim.cell_m, mean_temp(), rain_here(sim.heights))
        if sim.step == 0:
            sim.veg_snapshots[0] = (sim.state['veg'] * 255).astype(np.uint8)

    # fire (flame sensor or B): burns the plants around the fire, on the latest step only
    if (weather.burning() and weather.fire_spot and view_step is None
            and not showing_original and sim.state.get('veg') is not None):
        x, z = weather.fire_spot
        sim.state['veg'] = vegetation.burn(sim.state['veg'], sim.heights.shape,
                                           x / config.SCALE[0] + 0.5, z / config.SCALE[2] + 0.5)
        fires += 1

    step = 0 if showing_original else shown_step()
    veg = sim.veg_at(step)
    key = (sim.timeline, step, sim.version, fires, veg is None)
    if key == veg_shown:
        return
    veg_shown = key
    if veg is None:
        world.set_shader_input('veg_on', 0.0)
        return
    picture = np.flip(np.swapaxes(veg, 0, 1), axis=0)      # same orientation as the terrain
    tex = Texture(Image.fromarray((picture * 255).astype(np.uint8)))
    tex.filtering = 'bilinear'
    world.set_shader_input('veg_tex', tex)
    world.set_shader_input('veg_on', 1.0)


def plant_line():
    """One line of text about the plants."""
    veg = sim.veg_at(0 if showing_original else shown_step())
    if veg is None:
        return 'Plants: tick Vegetation to grow them   (B fire)'
    cap = vegetation.capacity(shown_heights(), sim.cell_m, mean_temp(), rain_here(shown_heights()))
    burned = ((veg < 0.3 * cap) & (cap > 0.3)).mean() * 100
    burn_text = f', {burned:.1f}% of the map burned (rivers erode faster there)' if burned > 0.05 else ''
    return (f"Plants: {veg.mean() * 100:.0f}% cover, sunlight x{climate.sunlight:.1f} (light sensor)"
            f"{burn_text}   (B fire)")


def live_sea_temp(step):
    """Sea-level temperature for the step being shown."""
    if 0 < step < sim.step:           # looking back: what it really was back then
        return sim.steps[step - 1]['sea_temp']
    if step == 0:                     # before the first step: the climate over one step of the chosen length
        return climate.sea_level_temp(0, panel.step_days)
    s = sim.steps[step - 1]
    return climate.sea_level_temp(s['start_day'], s['dt_days'])


def start_world(heights, texture, settings):
    """Called by the menu's START button: build the terrain, simulation and control panel."""
    global original, sim, world, ghost, rivers, weather, panel, orbit
    sensors.rezero()                          # every sensor's reading right now = "no change"

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
    rivers = RiverSystem(original, scale=config.SCALE,    # water.py owns all river behaviour
                         climate_now=water_climate())
    weather = Weather(config.SCALE, sensors)              # weather.py: rain, snow, wind, fire
    weather.enabled = config.WEATHER_ON

    camera.position = (0, 0, -110)
    orbit = EditorCamera()
    orbit.smoothing_helper.rotation_x = 50

    before = set(camera.ui.children)
    panel = ControlPanel(on_start_pause=toggle_running, on_reset=reset,
                         on_prev=lambda: step_view(-1), on_next=lambda: step_view(1),
                         on_likelihood=check_likelihood)
    # everything the panel just added to the screen, so H can hide it all (works with any ui.py)
    panel_widgets[:] = [e for e in camera.ui.children if e not in before]


menu = MainMenu(on_start=start_world)


# ---------------------------------------------------------------- keys
def input(key):
    global showing_original, speed, manual_warming, show_fps, manual_rain
    global manual_wind, manual_wind_toward, auto_orbit, ui_hidden
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
    elif key in ('[', '[ hold', 'left bracket', 'left bracket hold'):
        manual_rain = max(-config.ANNUAL_RAIN_MM, manual_rain - 100)     # drier
    elif key in (']', '] hold', 'right bracket', 'right bracket hold'):
        manual_rain += 100                                               # wetter
    elif key == 'f':
        show_fps = not show_fps
    elif key == 'v':
        weather.enabled = not weather.enabled
    elif key == 'b':
        weather.manual_fire = not weather.manual_fire     # test the fire without the flame sensor
    elif key == 'y':                                      # wind strength: calm -> breeze -> windy -> storm
        levels = [0.0, 0.3, 0.6, 1.0]
        manual_wind = levels[(min(range(4), key=lambda i: abs(levels[i] - manual_wind)) + 1) % 4]
    elif key in ('j', 'j hold'):
        manual_wind_toward = (manual_wind_toward - 15) % 360     # turn the wind
    elif key in ('k', 'k hold'):
        manual_wind_toward = (manual_wind_toward + 15) % 360
    elif key == 'x':
        auto_orbit = not auto_orbit                       # camera slowly circles the map
    elif key == 'h':                                      # hide / show all text and buttons
        ui_hidden = not ui_hidden
        info.enabled = not ui_hidden
        for widget in panel_widgets:
            widget.enabled = not ui_hidden


def sensor_lines():
    """Two lines of text describing the sensors and the climate change they cause."""
    if sensors.connected():
        strength, direction = sensors.wind()
        wind = f'{strength:.2f}' + (f' toward {direction:.0f} deg' if direction is not None else '')
        readings = (f"Sensors ({sensors.port}, Z = zero): temp {sensors.get('temp'):.1f} C | "
                    f"humidity {sensors.change('hum'):+.0f}% -> rain x{sensors.rain_factor():.1f} | "
                    f"sun x{sensors.sunlight():.1f} | fire {sensors.fire_level():.2f} "
                    f"(burns at {sensors_module.FIRE_RISE:.2f}) | wind {wind}")
    else:
        readings = f"Sensors: not connected ({sensors.error or 'connecting...'})"
    sea_temp = live_sea_temp(shown_step())
    freezing_m = sea_temp / climate.LAPSE_RATE
    climate_line = (f"Climate: {climate.warming_c:+.1f} C vs normal "
                    f"(sensor {sensors.temp_change():+.1f}, keys {manual_warming:+.1f})   "
                    f"Snow line: {freezing_m:,.0f} m   Rain: {rain_mm():.0f} mm/yr ([ ] keys)")
    info = rivers.info or {}
    balance = ''
    if info.get('evaporation') is not None:
        balance = (f"   evaporation {info['evaporation']:.0f} mm/yr, runoff {info['runoff']:.0f} mm/yr, "
                   f"{info['closed']} lakes don't overflow")
    strength, toward = current_wind()
    source = 'joystick' if sensors.has('tilt') else 'Y strength, J K turn'
    if strength >= 0.05:
        h = shown_heights()
        wet, dry = rain.describe(rain_here(h), h, sim.cell_m, toward)
        wind_line = (f"Wind: {rain.wind_speed_ms(strength):.0f} m/s toward {toward:.0f} deg ({source})   "
                     f"rain on windward slopes {wet:.0f} mm/yr, rain shadow {dry:.0f} mm/yr\n")
    else:
        wind_line = f"Wind: calm, rain falls evenly ({source})\n"
    water_line = (f"Water: lakes {rivers.lake_percent:.1f}% of map, rivers {rivers.river_percent:.1f}%"
                  f"{balance}   (W show/hide)")
    return readings + '\n' + climate_line + '\n' + wind_line + water_line + '\n' + plant_line()


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
    climate.rain_mm = rain_mm()                     # the simulation's rivers use it too
    climate.sunlight = sensors.sunlight() if sensors.has('light') else 1.0
    climate.wind_strength, climate.wind_toward = current_wind()   # moves the rain around (rain.py)
    if auto_orbit and orbit is not None:
        orbit.smoothing_helper.rotation_y += config.AUTO_ORBIT_SPEED * time.dt
    collect_likelihood()
    rivers.update(time.dt)

    if running:
        # Steps per second are set so the whole run takes RUN_SPEEDS[speed] seconds to watch,
        # whether it's 10 steps or 1000. (Before, it was 1 step per frame, so a 1000-step run
        # took ~17 s at 60 fps even though each step only takes a fraction of a millisecond.)
        if nonstop:
            step_credit += config.NONSTOP_SPEEDS[speed] * time.dt     # steady steps per second
        else:
            step_credit += panel.steps / config.RUN_SPEEDS[speed] * time.dt
        frame_start = time.perf_counter()
        while step_credit >= 1 and sim.step < run_goal:
            sim.advance(panel.step_days, panel.enabled())
            step_credit -= 1
            if time.perf_counter() - frame_start > 0.02:   # never spend more than 20 ms per frame
                break
        if sim.step >= run_goal:              # added all the steps asked for
            if nonstop:
                print(f'nonstop run stopped: reached {config.MAX_STEPS} steps (the memory for looking back is full)')
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
        rivers.entity.set_shader_input('freeze_line', climate.snow_line(sea_temp))   # lakes above it freeze
        weather.set_state(h, climate.snow_line(sea_temp), rain_mm(), rain_here(h))   # snow above, rain below
        update_vegetation()
        if not running and water_climate() != last_water_climate:
            # rain or temperature changed (sensor or keys): lakes grow or shrink
            show(original if showing_original else shown_heights(),
                 key='original' if showing_original else shown_step())

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
            target='' if run_goal is None else (' (nonstop)' if nonstop else f' / {run_goal}'),
            unit=panel.unit, days=sim.days_at(step), sea_temp=sea_temp,
            below_zero=climate.freezing_fraction(h, sea_temp) * 100,
            enabled=panel.enabled(),
            scores=(land_changed, soil_moved, h.sum(), h.std(), original.std(),
                    sim.washed_off_at(step)),
            likelihood=likelihood_score, runs=runs_used,
            speed=(f'{config.NONSTOP_SPEEDS[speed]} steps/s (keys 1 2 3)' if nonstop and run_goal is not None
                   else f'{config.RUN_SPEEDS[speed]:g} s per run (keys 1 2 3)')
                  + (f'   |   {fps_line}' if show_fps else f'   |   {config.VERSION}'),
            showing_original=showing_original, sensor_lines=sensor_lines(),
            likelihood_progress=None if likelihood_job is None
            else (likelihood_job.done_runs, likelihood_job.total_runs))


app.run()
