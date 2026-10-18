"""
ui.py - the control panel (right side) and the information text (top left).
"""

import math

from ursina import Text, Checkbox, Button, ButtonGroup, InputField, window

import climate
from config import (TIME_STEPS, DEFAULT_TIME_STEP, DEFAULT_STEPS, MAX_STEPS,
                    ENSEMBLE_RUNS, RELATIVE_TOLERANCE)
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
        self.time_step = ButtonGroup(list(TIME_STEPS), default=DEFAULT_TIME_STEP, max_x=3,
                                     position=(x, y - 0.03))
        y -= 0.17

        # how many steps to run: click the box and type a number
        Text('STEPS TO ADD (each Start)', position=(x, y + 0.025), scale=1.1)
        self.steps_field = InputField(default_value=str(DEFAULT_STEPS), max_lines=1,
                                      character_limit=len(str(MAX_STEPS)),
                                      limit_content_to='0123456789',
                                      scale=(0.12, 0.04), position=(x + 0.06, y - 0.02))
        self.steps_field.text = str(DEFAULT_STEPS)
        self.total_text = Text('', position=(x + 0.14, y - 0.008))   # "= 100,000 years"

        # buttons
        y -= 0.1
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
        return self.time_step.value           # 'Day', 'Season', 'Year', '100 yr', ...

    @property
    def step_days(self):
        return TIME_STEPS[self.unit]

    @property
    def steps(self):
        """The number typed in the box: how many steps Start adds (at least 1)."""
        typed = self.steps_field.text.strip()
        return max(1, min(MAX_STEPS, int(typed) if typed else 1))

    def typing(self):
        """True while the steps box is being typed in (so keys like R don't reset)."""
        return self.steps_field.active

    def refresh(self):
        """Update the 'how long' text next to the box."""
        self.total_text.text = '= ' + span_text(self.steps * self.step_days) + ' more'
        if self.typing():
            self.total_text.text += '\n(press Enter when done)'



def span_text(days):
    """A length of time in words: '45 days', '3.5 years', '250,000 years'."""
    years = days / 365
    if years < 1:
        return f'{days:.0f} days'
    if years < 10:
        return f'{years:.1f} years'
    return f'{years:,.0f} years'


def date_text(days):
    """'Year 2, day 45 (Winter)' from a number of days since the start.
    After 100 years the day and season stop mattering, so it just says '25,000 years in'."""
    if days >= 365 * 100:
        return f'{days / 365:,.0f} years in'
    year = int(days // 365) + 1
    day_of_year = int(days % 365)
    return f'Year {year}, day {day_of_year + 1} ({climate.season_name(day_of_year)})'


def hud_text(status, step, latest_step, target, unit, days, sea_temp, below_zero,
             enabled, scores, likelihood, runs, speed, showing_original, sensor_lines,
             likelihood_progress=None):
    land_changed, soil_moved, total_soil, roughness, original_roughness = scores
    looking_back = f'   (latest: {latest_step})' if step != latest_step else ''
    if likelihood_progress is not None:
        done, total = likelihood_progress
        likely = f'Likelihood: calculating... {done}/{total} runs'
    elif likelihood is None:
        likely = 'Likelihood: (press L, or finish the run)'
    elif math.isnan(likelihood):
        likely = 'Likelihood: nothing has changed enough to score yet'
    else:
        likely = (f'Likelihood of the step {latest_step} result: {likelihood:.0f}%  '
                  f'({runs} alternative runs changed the land by the same amount, '
                  f'within {RELATIVE_TOLERANCE:.0%})')

    return (
        f"{status}   Step {step}{target}{looking_back}   next: {unit} steps   {speed}"
        f"{'   SHOWING ORIGINAL' if showing_original else ''}\n"
        f"{date_text(days)}   Sea level {sea_temp:.1f} C   Below freezing: {below_zero:.0f}% of map\n"
        f"Active: {', '.join(enabled) if enabled else 'none'}\n"
        f"Space start/pause | R reset | Left/Right look back | L likelihood | O G M C U views | 1 2 3 speed | F fps\n"
        f"Up/Down warmer/colder | Z re-zero temperature sensor\n"
        f"{sensor_lines}\n"
        f"{likely}\n"
        f"Land changed:  {land_changed:.1f}%\n"
        f"Soil moved:    {soil_moved:.2f}%\n"
        f"Total soil:    {total_soil:,.0f}  (should never change)\n"
        f"Roughness:     {roughness:.2f}   (was {original_roughness:.2f})"
    )
