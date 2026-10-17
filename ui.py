"""
ui.py - the control panel (right side) and the information text (top left).
"""

from ursina import Text, Checkbox, Slider, Button, ButtonGroup, window

import climate
from config import TIME_STEPS, DEFAULT_TIME_STEP, ENSEMBLE_RUNS, TOLERANCE
from conditions import CONDITIONS


class ControlPanel:
    def __init__(self, on_start_pause, on_reset, on_prev, on_next, on_likelihood):
        x = window.top_right.x - 0.42
        y = 0.42

        # one checkbox per condition
        Text('CONDITIONS', position=(x, y), scale=1.1)
        self.checkboxes = {}
        for i, name in enumerate(CONDITIONS):
            row_y = y - 0.06 - i * 0.05
            self.checkboxes[name] = Checkbox(start_value=True, position=(x + 0.015, row_y))
            Text(name, position=(x + 0.045, row_y + 0.012))
        y -= 0.07 + len(CONDITIONS) * 0.05

        # how long one step is
        Text('TIME STEP', position=(x, y), scale=1.1)
        self.time_step = ButtonGroup(list(TIME_STEPS), default=DEFAULT_TIME_STEP,
                                     position=(x, y - 0.03))
        y -= 0.17

        # how many steps to run
        self.steps_label = Text('STEPS TO SIMULATE', position=(x, y + 0.075), scale=1.1)
        self.steps_slider = Slider(min=1, max=365, default=60, step=1, dynamic=True,
                                   position=(x, y), scale=0.75)

        # buttons
        y -= 0.08
        size = (0.18, 0.045)
        Button(text='Start / Pause', scale=size, position=(x + 0.09, y), on_click=on_start_pause)
        Button(text='Reset', scale=size, position=(x + 0.29, y), on_click=on_reset)
        Button(text='Prev step', scale=size, position=(x + 0.09, y - 0.06), on_click=on_prev)
        Button(text='Next step', scale=size, position=(x + 0.29, y - 0.06), on_click=on_next)
        Button(text='Likelihood', scale=(0.38, 0.045), position=(x + 0.19, y - 0.12),
               on_click=on_likelihood)

    def enabled(self):
        """Names of the ticked conditions."""
        return [name for name, box in self.checkboxes.items() if box.value]

    @property
    def unit(self):
        return self.time_step.value           # 'Day', 'Season' or 'Year'

    @property
    def step_days(self):
        return TIME_STEPS[self.unit]

    @property
    def target(self):
        return int(self.steps_slider.value)


def date_text(days):
    """'Year 2, day 45 (Winter)' from a number of days since the start."""
    year = int(days // 365) + 1
    day_of_year = int(days % 365)
    return f'Year {year}, day {day_of_year + 1} ({climate.season_name(day_of_year)})'


def hud_text(status, step, latest_step, target, unit, days, sea_temp, below_zero,
             enabled, scores, likelihood, runs, speed, showing_original):
    land_changed, soil_moved, total_soil, roughness, original_roughness = scores
    looking_back = f'   (latest: {latest_step})' if step != latest_step else ''
    if likelihood is None:
        likely = 'Likelihood: (press L, or finish the run)'
    else:
        likely = (f'Likelihood of the step {latest_step} result: {likelihood:.0f}%  '
                  f'({runs} alternative runs, within +-{TOLERANCE:g})')

    return (
        f"{status}   Step {step} / {target} ({unit}s){looking_back}   speed {speed}"
        f"{'   SHOWING ORIGINAL' if showing_original else ''}\n"
        f"{date_text(days)}   Sea level {sea_temp:.1f} C   Below freezing: {below_zero:.0f}% of map\n"
        f"Active: {', '.join(enabled) if enabled else 'none'}\n"
        f"Space start/pause | R reset | Left/Right look back | L likelihood | O G M C U views | 1 2 3 speed\n"
        f"{likely}\n"
        f"Land changed:  {land_changed:.1f}%\n"
        f"Soil moved:    {soil_moved:.2f}%\n"
        f"Total soil:    {total_soil:,.0f}  (should never change)\n"
        f"Roughness:     {roughness:.2f}   (was {original_roughness:.2f})"
    )