"""
menu.py - the main menu shown before the simulation starts.

  1. choose a map: one of the PNG maps in config.MAPS, or a generated noise map
     (noise_map.py, with a seed and frequency)
  2. describe the real place: width, lowest/highest point, temperatures
  3. Start -> calls on_start(heights, texture, settings)

settings is a dictionary like {'MAP_WIDTH_M': 10000.0, 'AVG_TEMP_C': 5.0, ...}; the names
match config.py, so main.py can copy them straight into config.
"""

import random

from ursina import Entity, Text, Button, ButtonGroup, InputField, Texture, camera, color

import config
import maps

# the boxes on the right: (name in config.py, label on screen)
SETTINGS = [
    ('MAP_WIDTH_M', 'Map width (m)'),
    ('MIN_ELEVATION_M', 'Lowest point (m)'),
    ('MAX_ELEVATION_M', 'Highest point (m)'),
    ('AVG_TEMP_C', 'Average temperature (C)'),
    ('SEASON_SWING_C', 'Summer/winter swing (C)'),
]


class MainMenu(Entity):
    def __init__(self, on_start):
        super().__init__(parent=camera.ui)      # everything below is inside this, so hiding it hides all
        self.on_start = on_start

        # dark background behind the menu
        Entity(parent=self, model='quad', color=color.black66, scale=(1.75, 0.95), z=1)
        Text('WORLD IN A BOX', parent=self, position=(0, 0.42), origin=(0, 0), scale=2.5)

        # ---- 1. choose a map (left)
        x = -0.8
        Text('1. CHOOSE A MAP', parent=self, position=(x, 0.3), scale=1.2)
        self.map_choice = ButtonGroup(maps.map_names(), max_x=1, parent=self,
                                      position=(x, 0.24))
        seed_y = 0.24 - 0.05 * len(maps.map_names()) - 0.08
        Text('Seed (generated map):', parent=self, position=(x, seed_y))
        self.seed_field = InputField(parent=self, default_value='1', character_limit=6,
                                     limit_content_to='0123456789',
                                     scale=(0.12, 0.04), position=(x + 0.06, seed_y - 0.05))
        self.seed_field.text = '1'
        Button('New seed', parent=self, scale=(0.14, 0.04), position=(x + 0.22, seed_y - 0.05),
               on_click=self.new_seed)
        Text('Frequency (higher = steeper hills):', parent=self, position=(x, seed_y - 0.1))
        self.frequency_field = InputField(parent=self, default_value='1.5', character_limit=5,
                                          limit_content_to='0123456789.',
                                          scale=(0.12, 0.04), position=(x + 0.06, seed_y - 0.15))
        self.frequency_field.text = '1.5'

        # ---- preview of the chosen map (middle)
        self.preview = Entity(parent=self, model='quad', scale=0.42, position=(-0.02, -0.02))
        self.preview_text = Text('', parent=self, position=(-0.02, -0.26), origin=(0, 0))

        # ---- 2. describe the place (right)
        x = 0.3
        Text('2. DESCRIBE THE PLACE', parent=self, position=(x, 0.3), scale=1.2)
        self.fields = {}
        for i, (name, label) in enumerate(SETTINGS):
            y = 0.22 - i * 0.08
            Text(label, parent=self, position=(x, y + 0.012))
            field = InputField(parent=self, default_value=str(getattr(config, name)),
                               character_limit=8, limit_content_to='0123456789.-',
                               scale=(0.16, 0.04), position=(x + 0.4, y))
            field.text = str(getattr(config, name))
            self.fields[name] = field

        # ---- start
        Button('START', parent=self, scale=(0.3, 0.07), position=(0, -0.36),
               color=color.azure, on_click=self.start)
        self.error_text = Text('', parent=self, position=(0, -0.43), origin=(0, 0), color=color.red)

        self.heights = None
        self.texture_file = None
        self.shown = None             # which (map, seed) the preview is showing

    # ------------------------------------------------------------ actions
    def new_seed(self):
        self.seed_field.text = str(random.randint(1, 999999))
        self.map_choice.value = [maps.GENERATED]      # a new seed only makes sense for generated

    def seed(self):
        typed = self.seed_field.text.strip()
        return int(typed) if typed else 1

    def frequency(self):
        try:
            return max(0.1, float(self.frequency_field.text))
        except ValueError:                 # empty box or just "."
            return 1.5

    def update(self):
        """Every frame: if the chosen map, seed or frequency changed, load it and update the preview."""
        if not self.enabled:
            return
        choice = self.map_choice.value
        generated = choice == maps.GENERATED
        wanted = (choice, self.seed() if generated else None, self.frequency() if generated else None)
        if wanted == self.shown:
            return
        self.shown = wanted
        try:
            if generated:
                self.heights = maps.generate_heights(self.seed(), self.frequency())
                self.texture_file = None
                self.preview.texture = Texture(maps.preview_image(self.heights))
                self.preview_text.text = f'Generated map, seed {self.seed()}, frequency {self.frequency():g}'
            else:
                heightmap, self.texture_file = config.MAPS[choice]
                self.heights = maps.load_heightmap(heightmap)
                shown = self.texture_file or heightmap          # show the texture if there is one
                self.preview.texture = Texture(maps.find_file(shown))
                self.preview_text.text = heightmap
            size = self.heights.shape
            self.preview_text.text += f'\n{size[0]} x {size[1]} points'
            self.error_text.text = ''
        except Exception as problem:                       # e.g. a PNG name typed wrong
            self.heights = None
            self.preview.texture = None
            self.error_text.text = str(problem)

    def read_settings(self):
        """The numbers typed in the boxes, checked. Returns (settings, problem)."""
        settings = {}
        for name, label in SETTINGS:
            try:
                settings[name] = float(self.fields[name].text)
            except ValueError:
                return None, f'"{label}" needs a number'
        if settings['MAP_WIDTH_M'] <= 0:
            return None, 'Map width must be more than 0'
        if settings['MAX_ELEVATION_M'] <= settings['MIN_ELEVATION_M']:
            return None, 'Highest point must be higher than the lowest point'
        if settings['SEASON_SWING_C'] < 0:
            return None, 'Summer/winter swing cannot be negative'
        return settings, None

    def start(self):
        if self.heights is None:
            self.error_text.text = 'Choose a map that loads first'
            return
        settings, problem = self.read_settings()
        if problem:
            self.error_text.text = problem
            return
        self.enabled = False
        self.on_start(self.heights, self.texture_file, settings)

    def typing(self):
        """True while any box in the menu is being typed in."""
        boxes = [self.seed_field, self.frequency_field] + list(self.fields.values())
        return self.enabled and any(box.active for box in boxes)
