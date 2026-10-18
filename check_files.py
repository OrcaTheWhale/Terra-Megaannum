"""
check_files.py - quick test that every file is in place and working.
Run:  python check_files.py
"""

import traceback

import numpy as np

results = []


def check(name, test):
    try:
        ok, detail = test()
    except Exception:
        ok, detail = False, traceback.format_exc().strip().splitlines()[-1]
    results.append((name, ok, detail))


def test_config():
    import config
    ok = '10k yr' in config.TIME_STEPS and 'creep_d' in config.PARAMS and len(config.MAPS) > 0
    return ok, f'maps {list(config.MAPS)}, creep D {config.PARAMS["creep_d"]} m2/yr'


def test_climate():
    import climate
    july = climate.sea_level_temp(200, 1)
    january = climate.sea_level_temp(17, 1)
    year = climate.sea_level_temp(0, 365)
    line = climate.snow_line(6.5)          # 6.5 C at sea level -> 0 C at 1000 m -> 1000/1500 of the way up
    ok = (abs(july - 20) < 0.1 and abs(january + 10) < 0.1 and abs(year - 5) < 1e-6
          and abs(line - 1000 / 1500) < 1e-9)
    return ok, f'July {july:.1f} C, January {january:.1f} C, year {year:.1f} C, snow line ok: {ok}'


def test_conditions():
    import conditions
    p = {'creep_d': 0.005, 'dt_days': 365 * 1_000_000, 'cell_m': 160}
    h = np.random.rand(20, 20) * 255
    out = conditions.soil_creep(h, p)
    conserved = np.isclose(h.sum(), out.sum())
    smoother = out.std() < h.std()

    # Physics check: a smooth wave of hills should shrink exactly like the maths says,
    # amplitude x exp(-D k^2 t)  (the known solution of the diffusion equation).
    n, cell, D, years = 40, 160, 0.005, 30_000_000
    x = (np.arange(n) + 0.5) * cell
    k = 3 * np.pi / (n * cell)                 # 3 half-waves across the map
    wave = 100 + 10 * np.cos(k * x)[:, None] * np.ones((1, n))
    out2 = conditions.soil_creep(wave, {'creep_d': D, 'dt_days': 365 * years, 'cell_m': cell})
    got = (out2[0, 0] - 100) / (10 * np.cos(k * x[0]))
    expected = np.exp(-D * k ** 2 * years)
    matches = abs(got - expected) < 0.01
    ok = conserved and smoother and matches
    return ok, (f'soil conserved: {conserved}, smoother: {smoother}, '
                f'matches exact solution: {matches} ({got:.3f} vs {expected:.3f})')


def test_analysis():
    import analysis
    o = np.full((10, 10), 100.0)
    h = o.copy()
    h[0, 0], h[0, 1] = 90, 110
    land, soil = analysis.change_scores(h, o)
    ok = np.isclose(land, 2.0) and np.isclose(soil, 0.1)
    return ok, f'land changed {land:.1f}%, soil moved {soil:.2f}%'


def test_simulation():
    from simulation import Simulation
    s = Simulation(np.random.rand(20, 20) * 255)
    s.advance(91.25, ['Soil creep'])
    s.advance(91.25, ['Soil creep'])
    after_two = (s.step, s.elapsed_days, round(s.steps[0]['sea_temp'], 1))
    s.rewind_to(1)
    after_rewind = (s.step, s.elapsed_days)
    ok = after_two == (2, 182.5, -7.0) and after_rewind == (1, 91.25)
    return ok, f'after 2 seasons {after_two}, after rewind {after_rewind}'


def test_ui():
    import ui
    text = ui.date_text(400)
    long = ui.span_text(365 * 250_000)
    return text == 'Year 2, day 36 (Winter)' and long == '250,000 years', f'{text} | {long}'



def test_maps():
    import config
    import maps
    first = list(config.MAPS)[0]
    real = maps.load_heightmap(config.MAPS[first][0])
    made = maps.generate_heights(42)
    same_again = np.array_equal(made, maps.generate_heights(42))     # same seed -> same map
    size = (config.GRID_SIZE, config.GRID_SIZE)
    ok = real.shape == size and made.shape == size and made.min() == 0 and made.max() == 255 and same_again
    return ok, f'{first}: {real.shape}, generated: {made.shape}, same seed same map: {same_again}'


def test_water():
    import water
    # a bowl: a hollow in the middle should fill up into one lake, with no water stuck anywhere
    x, z = np.meshgrid(np.linspace(-1, 1, 30), np.linspace(-1, 1, 30))
    bowl = 100 + 50 * (x ** 2 + z ** 2) - 60 * np.exp(-(x ** 2 + z ** 2) * 8)
    filled, lakes, rivers, flow, min_flow = water.find_water(bowl)
    stuck = (water.find_downhill(filled).reshape(bowl.shape)[1:-1, 1:-1] == -1).sum()
    ok = lakes[15, 15] and stuck == 0 and filled.min() >= bowl.min()
    return ok, f'lake in the hollow: {bool(lakes[15, 15])}, water stuck inside the map: {stuck}'


def test_menu_present():
    source = open('menu.py', encoding='utf-8').read()
    return 'class MainMenu' in source, 'MainMenu found'


def test_terrain_handler():
    import TerrainHandler
    return hasattr(TerrainHandler, 'FastTerrain'), 'FastTerrain found'


def test_main_present():
    source = open('main.py', encoding='utf-8').read()
    ok = 'def start_world' in source and 'MainMenu' in source and 'terrain_shader' in source
    return ok, 'main.py starts from the menu' if ok else 'main.py is still the old version'


check('config.py', test_config)
check('climate.py', test_climate)
check('conditions.py', test_conditions)
check('analysis.py', test_analysis)
check('simulation.py', test_simulation)
check('ui.py', test_ui)
check('maps.py', test_maps)
check('water.py', test_water)
check('menu.py', test_menu_present)
check('TerrainHandler.py', test_terrain_handler)
check('main.py', test_main_present)

import config
print(f'\n================ FILE CHECK ({config.VERSION}) ================')
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name:<18} {detail}")
failed = [name for name, ok, _ in results if not ok]
print('============================================')
print('All good! Run: python main.py' if not failed else f'Fix these first: {", ".join(failed)}')
