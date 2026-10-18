"""
config.py - every setting and number in one place.
Change values here instead of hunting through the other files.
"""

VERSION = 'v23'              # shown in the window title, the terminal and check_files.py

# ---------------------------------------------------------------- maps
# The maps you can pick in the menu: name -> (heightmap PNG, texture PNG or None).
# To add one, put the PNGs in this folder (or a maps/ folder) and add a line here.
MAPS = {
    'Real place': ("Height Map PNG.png", "Texture PNG.png"),
}

# How the terrain is coloured:
#   'blend'   grass / rock on steep slopes / snow above the snow line (terrain_shader.py)
#   'texture' the map's own texture PNG from MAPS (generated maps still use 'blend')
TERRAIN_LOOK = 'blend'
TERRAIN_TEXTURES = {
    'grass_tex': "assets/textures/Grass002_1K-JPG_Color.jpg",
    'rock_tex': "assets/textures/Rock050_1K-JPG_Color.jpg",
    'snow_tex': "assets/textures/Snow010A_1K-JPG_Color.jpg",
    'dirt_tex': "assets/textures/Ground048_1K-JPG_Color.jpg"
}
GENERATED_COLOR = (0.45, 0.62, 0.38)   # used only if the blend textures can't be found, 0-1 RGB

# ---------------------------------------------------------------- display
GRID_SIZE = 128             # points across the terrain. Every map (any PNG size) is resized to this.
                            # 64 = fastest, 128 = good balance, 256 = sharp but slow (water ~10x slower)
SCALE = (35, 35, 35)        # (width, height, depth) of the terrain on screen

# ---------------------------------------------------------------- weather effects (weather.py)
WEATHER_ON = True           # V key shows/hides it
RAIN_FOR_FULL_WEATHER = 1500   # yearly rain (mm) that shows the heaviest rain/snow effect
WIND_STRENGTH = 0.3         # 0-1, used when the joystick isn't connected
WIND_TOWARD_DEG = 45        # direction the wind blows toward, when the joystick gives none
AUTO_ORBIT_SPEED = 6        # degrees per second the camera circles with X (a full circle in 1 minute)
PRECIP_PER_TICK = 40        # raindrops/snowflakes started 10x a second at full intensity
MAX_RAIN = 350              # most particles alive at once (more = prettier but slower)
MAX_SNOW = 300
MAX_WIND = 40
MAX_FLAMES = 80
MAX_SMOKE = 30

# ---------------------------------------------------------------- sensors
SENSOR_PORT = None          # e.g. "COM5". None = find the ESP32 automatically

# ---------------------------------------------------------------- the real place
# Starting values for the menu boxes; whatever is typed in the menu replaces them.
MIN_ELEVATION_M = 0         # lowest point of the map, in metres
MAX_ELEVATION_M = 1500      # highest point of the map, in metres
MAP_WIDTH_M = 10000         # real width of the area the map shows, in metres (10000 = 10 km)

# ---------------------------------------------------------------- time
# How much time one simulation step represents, in days.
TIME_STEPS = {
    'Day': 1,
    'Season': 365 / 4,
    'Year': 365,
    '100 yr': 365 * 100,
    '1,000 yr': 365 * 1000,
    '10k yr': 365 * 10000,
}
DEFAULT_TIME_STEP = '1,000 yr'
DEFAULT_STEPS = 100         # how many steps each Start adds (typed in the box on screen)
MAX_STEPS = 10000           # most steps in total: every step is kept for looking back
SNAPSHOT_MEMORY_MB = 400    # ...but never more steps than fit in this much memory
                            # (each step stores the terrain: 64 KB at GRID_SIZE 128 -> about 6,000 steps)

# How long a whole run takes to watch, in seconds, for keys 1 / 2 / 3 (however many steps it has).
RUN_SPEEDS = {'1': 15, '2': 5, '3': 1}
DEFAULT_SPEED = '2'
# nonstop runs (0 in the steps box): steps per second for keys 1 2 3
NONSTOP_SPEEDS = {'1': 2, '2': 10, '3': 40}
WATER_REDRAW_SECONDS = 0.3  # while running, work the water out again this often (in the background,
                            # so it doesn't slow the app). 0 = only when a run pauses or ends

# ---------------------------------------------------------------- climate (sea level)
# Replace with real climate normals for your place (average of the 12 monthly averages,
# and half the gap between the warmest and coldest month).
AVG_TEMP_C = 5              # yearly average temperature at sea level
SEASON_SWING_C = 15         # how far summer and winter go above / below the average
WARMEST_DAY = 200           # day of the year that's warmest on average (200 = mid-July)
ANNUAL_RAIN_MM = 800        # yearly rain + snow (mm). ~200 desert, ~800 temperate, ~2000+ rainforest

# ---------------------------------------------------------------- model parameters
# The numbers the conditions use, in real-world units. Conditions scale them to the step length.
PARAMS = {
    # Soil creep "diffusivity" in m^2 per year. Measured values are about 0.001 to 0.01
    # (about 0.005 for humid, vegetated hills; up to ~0.017 for frost-heaved bare ground).
    'creep_d': 0.005,
    # Tectonic uplift in the middle of the map, in mm per year (the map edges stay put).
    # Real rates: ~0.01-0.1 old ranges (Appalachians), ~1-2 Alps, ~5-10 Himalaya.
    'uplift_mm_yr': 0.3,
    # River erosion "erodibility" K in the stream power law E = K * A^0.5 * slope (per year,
    # A in m^2). Published values span ~1e-7 (hard rock) to ~1e-4 (soft sediment); 2e-6 gives
    # ~0.1 mm/yr average erosion on this map, typical of mountain ranges.
    'river_k': 2e-6,
    # How easily sediment settles out of rivers (G in the xi-q model, around 0.1-1).
    'deposition_g': 0.5,
    # Vegetation: growth rate (per year; 0.15 = a burned forest is mostly back in ~30 years),
    # how fast plants spread into neighbouring ground, and how much full plant cover slows
    # river erosion (0.7 = 70% slower; roots hold the soil).
    'veg_growth': 0.15,
    'veg_spread': 300,          # m2/yr: how fast plants spread into bare ground (seeds); front speed 2*sqrt(growth*spread) = 13 m/yr
    'veg_protection': 0.7,
}

# How unsure we are about each parameter (0.8 = could be 80% higher or lower).
UNCERTAINTY = {
    'creep_d': 0.8,          # 0.001 to 0.009: roughly the measured range
    'uplift_mm_yr': 0.5,
    'river_k': 0.7,          # K is only known roughly for a given rock type
    'deposition_g': 0.5,
    'veg_growth': 0.3,
    'veg_protection': 0.3,
}

# Conditions ticked when the app starts (the others start unticked)
CONDITIONS_ON = ['Soil creep', 'Vegetation', 'River erosion']

# ---------------------------------------------------------------- likelihood score
AUTO_LIKELIHOOD = True      # work out the likelihood automatically when a run ends (False = only with L)
HEIGHT_ERROR = 1.0          # the PNG stores whole numbers, so each height could be off by up to 1
ENSEMBLE_RUNS = 20          # how many alternative runs to compare against (at most)
ENSEMBLE_TIME_LIMIT = 6.0   # seconds: fewer runs are used if 20 would take longer than this
# The score only looks at land that changed by more than MIN_CHANGE (unchanged land always
# "agrees", which made the score look like 100%). A run agrees at a point if it changed it by
# the same amount, within RELATIVE_TOLERANCE (25%), or within TOLERANCE height units if that's bigger.
MIN_CHANGE = 2.0            # height units
RELATIVE_TOLERANCE = 0.25
TOLERANCE = 1.0             # height units
