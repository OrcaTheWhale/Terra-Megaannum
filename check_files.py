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
    ok = config.TIME_STEPS == {'Day': 1, 'Season': 91.25, 'Year': 365}
    return ok, f'scale {config.SCALE}, time steps {config.TIME_STEPS}'


def test_climate():
    import climate
    july = climate.sea_level_temp(200, 1)
    january = climate.sea_level_temp(17, 1)
    year = climate.sea_level_temp(0, 365)
    ok = abs(july - 20) < 0.1 and abs(january + 10) < 0.1 and abs(year - 5) < 1e-6
    return ok, f'July {july:.1f} C, January {january:.1f} C, whole year {year:.1f} C'


def test_conditions():
    import conditions
    h = np.random.rand(20, 20) * 255
    out = conditions.soil_creep(h, {'creep_rate': 0.05, 'dt_days': 365})
    conserved = np.isclose(h.sum(), out.sum())
    smoother = out.std() < h.std()
    return conserved and smoother, f'soil conserved: {conserved}, smoother: {smoother}'


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
    return text == 'Year 2, day 36 (Winter)', text


def test_terrain_handler():
    import TerrainHandler
    return hasattr(TerrainHandler, 'FastTerrain'), 'FastTerrain found'


def test_main_present():
    source = open('main.py', encoding='utf-8').read()
    ok = 'from simulation import Simulation' in source and 'ControlPanel' in source
    return ok, 'new main.py' if ok else 'main.py is still the old version'


check('config.py', test_config)
check('climate.py', test_climate)
check('conditions.py', test_conditions)
check('analysis.py', test_analysis)
check('simulation.py', test_simulation)
check('ui.py', test_ui)
check('TerrainHandler.py', test_terrain_handler)
check('main.py', test_main_present)

print('\n================ FILE CHECK ================')
for name, ok, detail in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name:<18} {detail}")
failed = [name for name, ok, _ in results if not ok]
print('============================================')
print('All good! Run: python main.py' if not failed else f'Fix these first: {", ".join(failed)}')