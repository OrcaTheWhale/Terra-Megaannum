"""weather.py - decides what weather particle.py shows (amount, snow vs rain, wind,
more drops on windward slopes), plus the fire and smoke.
"""

import math
import random

import climate

from ursina import Entity, Vec3, color, destroy, time

import config
import particle


# ---------------------------------------------------------------- particles
class Flame(Entity):
    def __init__(self, weather, position):
        super().__init__(parent=weather, model='quad', billboard=True, position=position,
                         color=color.rgba(1, random.uniform(0.45, 0.8), 0.1, 0.9),
                         scale=random.uniform(0.25, 0.5))
        self.velocity = Vec3(random.uniform(-0.3, 0.3), random.uniform(1.5, 3), random.uniform(-0.3, 0.3))
        self.life = self.start_life = random.uniform(0.5, 1.0)

    def update(self):
        self.position += self.velocity * time.dt
        self.life -= time.dt
        self.alpha = max(0, self.life / self.start_life)          # fade out as it rises
        if self.life <= 0:
            destroy(self)


class Smoke(Entity):
    def __init__(self, weather, position, drift):
        super().__init__(parent=weather, model='quad', billboard=True, position=position,
                         color=color.rgba(0.3, 0.3, 0.3, 0.5), scale=random.uniform(0.6, 1.0))
        self.velocity = Vec3(drift[0] * 3 + random.uniform(-0.2, 0.2), random.uniform(1, 2),
                             drift[1] * 3 + random.uniform(-0.2, 0.2))
        self.life = self.start_life = random.uniform(2, 3.5)

    def update(self):
        self.position += self.velocity * time.dt
        self.scale *= 1 + 0.4 * time.dt                           # smoke spreads out
        self.life -= time.dt
        self.alpha = 0.5 * max(0, self.life / self.start_life)
        if self.life <= 0:
            destroy(self)


# ---------------------------------------------------------------- the weather controller
class Weather(Entity):
    """Spawns the particles. main.py calls set_state() with the terrain shown and the snow line."""

    def __init__(self, scale, sensors):
        super().__init__()
        self.sx, self.sy, self.sz = scale
        self.sensors = sensors
        self.heights = None
        self.snow_line = 2.0             # 0-1 height where it's 0 C (above 1 = no snow anywhere)
        self.timer = 0.0
        self.rain = config.ANNUAL_RAIN_MM   # yearly rain (mm), set by main.py
        self.rain_map = None             # yearly rain at every point (wind-driven rain), from main.py
        self.fire_spot = None            # (x, z) while something is burning
        self.manual_fire = False         # B key, for testing without the flame sensor

        # the VFX teammate's particles (particle.py), steered from update()
        half = (self.sx / 2, self.sz / 2)
        self.rain_fx = particle.rain(size=half, life=20, spawn_point=lambda: self.drop_start('rain'),
                                     ground=self.ground_y, max_particles=config.MAX_RAIN)
        self.snow_fx = particle.snow(size=half, life=60, spawn_point=lambda: self.drop_start('snow'),
                                     ground=self.ground_y, max_particles=config.MAX_SNOW)
        self.wind_fx = particle.wind(size=(self.sx / 2, self.sy * 0.25), speed=5,
                                     distance=self.sx * 0.8, height=self.sy * 0.75,
                                     max_particles=config.MAX_WIND)
        for fx in (self.rain_fx, self.snow_fx, self.wind_fx):
            fx.parent = self

    def set_state(self, heights, snow_line, rain_mm, rain_map=None):
        self.heights = heights
        self.snow_line = snow_line
        self.rain = rain_mm
        self.rain_map = rain_map

    def rain_spot(self):
        """A random point to drop rain/snow from, picked more often where it rains more
        (wind-driven rain: the windward slopes get more drops, the rain shadow fewer)."""
        r = self.rain_map
        if r is None:
            return self.random_point()
        top = r.max()
        for _ in range(20):
            x, z = self.random_point()
            n, m = r.shape
            i = min(n - 1, max(0, int(round((x / self.sx + 0.5) * (n - 1)))))
            j = min(m - 1, max(0, int(round((z / self.sz + 0.5) * (m - 1)))))
            if random.random() * top <= r[i, j]:
                return x, z
        return x, z

    # ------------------------------------------------------------ helpers
    def ground_y(self, x, z):
        """Height of the terrain (in world units) under a point."""
        h = self.heights
        n, m = h.shape
        i = min(n - 1, max(0, int(round((x / self.sx + 0.5) * (n - 1)))))
        j = min(m - 1, max(0, int(round((z / self.sz + 0.5) * (m - 1)))))
        return h[i, j] / 255 * self.sy

    def ground_fraction(self, x, z):
        return self.ground_y(x, z) / self.sy

    def rain_amount(self):
        """0-1: how heavy the rain/snow effect is, from the yearly rain."""
        return min(1.0, self.rain / config.RAIN_FOR_FULL_WEATHER)

    def wind(self):
        """(strength 0-1, heading in degrees the wind blows TOWARD)."""
        return climate.wind_strength, climate.wind_toward     # main.py sets these (sensor or keys)

    def burning(self):
        if self.manual_fire:
            return True
        import sensors as sensors_module
        return self.sensors.has('flame') and self.sensors.fire_level() > sensors_module.FIRE_RISE

    def count(self, kind):
        return sum(1 for e in self.children if isinstance(e, kind))

    def top(self):
        """Height the clouds drop rain and snow from."""
        return max(self.sy, self.heights.max() / 255 * self.sy) * 1.15

    def drop_start(self, kind):
        """Where a raindrop / snowflake starts: a landing spot that suits it, moved upwind."""
        if self.heights is None:
            return None
        fx = self.rain_fx if kind == 'rain' else self.snow_fx
        fall_speed = 5 if kind == 'rain' else 1               # particle.py's fall speeds
        drift_x = -fx.windspeed * 0.2 * math.cos(fx.windangle)
        drift_z = -fx.windspeed * 0.2 * math.sin(fx.windangle)
        top = self.top()
        for _ in range(10):
            x, z = self.rain_spot()
            ground = self.ground_y(x, z)
            snowy = ground / self.sy >= self.snow_line
            if snowy == (kind == 'snow'):
                t = (top - ground) / fall_speed                # seconds to fall
                ox = max(-self.sx, min(self.sx, drift_x * t))
                oz = max(-self.sz, min(self.sz, drift_z * t))
                return (x - ox, top, z - oz)
        return None                                           # none of this kind right now

    def random_point(self):
        return random.uniform(-self.sx / 2, self.sx / 2), random.uniform(-self.sz / 2, self.sz / 2)

    # ------------------------------------------------------------ every frame
    def update(self):
        if self.heights is None:
            return
        self.timer -= time.dt
        if self.timer > 0:
            return
        self.timer = 0.1                                  # spawn 10 times a second

        strength, heading = self.wind()
        a = math.radians(heading)
        drift = (strength * math.cos(a), strength * math.sin(a))
        speed_ms = (2 + 18 * strength) if strength >= 0.05 else 0.0    # same wind speed as rain.py

        # rain and snow (particle.py): how much, and which way the wind pushes them.
        # particle.py moves drops toward -(cos, sin) of windangle, so it's the direction the
        # wind comes FROM; its spawn count per 0.1 s is size_x * size_z * intensity / 200.
        amount = self.rain_amount()
        per_tick = config.PRECIP_PER_TICK * amount
        area = (self.sx / 2) * (self.sz / 2)
        snowy = float((self.heights / 255 >= self.snow_line).mean())   # share of the map that's snowy
        for fx, share in ((self.rain_fx, 1 - snowy), (self.snow_fx, snowy)):
            fx.intensity = per_tick * share * 200 / area if amount > 0.05 else 0.0
            fx.windspeed = speed_ms
            fx.windangle = a + math.pi

        # wind streaks (particle.py): they start on the angle's side and blow across, so the
        # angle is where the wind comes from
        self.wind_fx.angle = heading + 180
        self.wind_fx.speed = 4 + 10 * strength
        wind_area = self.wind_fx.size[0] * self.wind_fx.size[1]
        self.wind_fx.intensity = (1 + 3 * strength) * 200 / wind_area if strength > 0.05 else 0.0

        # fire: flames and smoke on a spot below the snow line, while the flame sensor sees fire
        if self.burning():
            if self.fire_spot is None:
                for _ in range(50):                       # find somewhere that isn't snowy
                    x, z = self.random_point()
                    if self.ground_fraction(x, z) < self.snow_line:
                        break
                self.fire_spot = (x, z)
            fx, fz = self.fire_spot
            for _ in range(min(6, config.MAX_FLAMES - self.count(Flame))):
                x, z = fx + random.uniform(-1, 1), fz + random.uniform(-1, 1)
                Flame(self, (x, self.ground_y(x, z) + 0.1, z))
            if self.count(Smoke) < config.MAX_SMOKE:
                Smoke(self, (fx, self.ground_y(fx, fz) + 1, fz), drift)
        else:
            self.fire_spot = None
