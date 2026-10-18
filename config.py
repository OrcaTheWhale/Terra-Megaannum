"""
config.py - every setting and number in one place.
Change values here instead of hunting through the other files.
"""

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
    'grass_tex': "textures/Grass002_2K-PNG/Grass002_2K-PNG_Color.png",
    'rock_tex': "textures/Rock050_2K-PNG/Rock050_2K-PNG_Color.png",
    'snow_tex': "textures/Snow010A_2K-PNG/Snow010A_2K-PNG_Color.png",
}
GENERATED_COLOR = (0.45, 0.62, 0.38)   # used only if the blend textures can't be found, 0-1 RGB

# ---------------------------------------------------------------- display
GRID_SIZE = 128             # points across the terrain. Every map (any PNG size) is resized to this.
                            # 64 = fastest, 128 = good balance, 256 = sharp but slow (water ~10x slower)
SCALE = (35, 35, 35)        # (width, height, depth) of the terrain on screen

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
WATER_REDRAW_SECONDS = 0    # while running, work the water out fully this often (it's the slow part).
                            # 0 = only when a run pauses or ends (smoothest); in between it follows the ground

# ---------------------------------------------------------------- climate (sea level)
# Replace with real climate normals for your place (average of the 12 monthly averages,
# and half the gap between the warmest and coldest month).
AVG_TEMP_C = 5              # yearly average temperature at sea level
SEASON_SWING_C = 15         # how far summer and winter go above / below the average
WARMEST_DAY = 200           # day of the year that's warmest on average (200 = mid-July)

# ---------------------------------------------------------------- model parameters
# The numbers the conditions use, in real-world units. Conditions scale them to the step length.
PARAMS = {
    # Soil creep "diffusivity" in m^2 per year. Measured values are about 0.001 to 0.01
    # (about 0.005 for humid, vegetated hills; up to ~0.017 for frost-heaved bare ground).
    'creep_d': 0.005,
}

# How unsure we are about each parameter (0.8 = could be 80% higher or lower).
UNCERTAINTY = {
    'creep_d': 0.8,          # 0.001 to 0.009: roughly the measured range
}

# ---------------------------------------------------------------- likelihood score
HEIGHT_ERROR = 1.0          # the PNG stores whole numbers, so each height could be off by up to 1
ENSEMBLE_RUNS = 20          # how many alternative runs to compare against (at most)
ENSEMBLE_TIME_LIMIT = 3.0   # seconds: fewer runs are used if 20 would take longer than this
TOLERANCE = 2.0             # how close (height units) a run must be to count as "the same result"
