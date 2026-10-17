"""
config.py - every setting and number in one place.
Change values here instead of hunting through the other files.
"""

# ---------------------------------------------------------------- files and display
HEIGHTMAP = "Height Map PNG.png"
TEXTURE = "Texture PNG.png"
SKIP = 4                    # shrink the terrain when loading (1, 2, 4, 8...). Bigger = faster
SCALE = (35, 35, 35)        # (width, height, depth) of the terrain on screen

# ---------------------------------------------------------------- the real place
# Fill these in for your heightmap so heights can be turned into metres.
MIN_ELEVATION_M = 0         # lowest point of the map, in metres
MAX_ELEVATION_M = 1500      # highest point of the map, in metres

# ---------------------------------------------------------------- time
# How much time one simulation step represents, in days.
TIME_STEPS = {
    'Day': 1,
    'Season': 365 / 4,
    'Year': 365,
}
DEFAULT_TIME_STEP = 'Day'

# ---------------------------------------------------------------- climate (sea level)
# Replace with real climate normals for your place (average of the 12 monthly averages,
# and half the gap between the warmest and coldest month).
AVG_TEMP_C = 5              # yearly average temperature at sea level
SEASON_SWING_C = 15         # how far summer and winter go above / below the average
WARMEST_DAY = 200           # day of the year that's warmest on average (200 = mid-July)

# ---------------------------------------------------------------- model parameters
# The numbers the conditions use. Rates are PER DAY; conditions scale them to the step length.
PARAMS = {
    'creep_rate': 0.05,     # soil creep, sped up a lot so changes are visible in a demo
}

# How unsure we are about each parameter (0.25 = could be 25% higher or lower).
UNCERTAINTY = {
    'creep_rate': 0.25,
}

# ---------------------------------------------------------------- likelihood score
HEIGHT_ERROR = 1.0          # the PNG stores whole numbers, so each height could be off by up to 1
ENSEMBLE_RUNS = 20          # how many alternative runs to compare against (at most)
ENSEMBLE_TIME_LIMIT = 3.0   # seconds: fewer runs are used if 20 would take longer than this
TOLERANCE = 2.0             # how close (height units) a run must be to count as "the same result"