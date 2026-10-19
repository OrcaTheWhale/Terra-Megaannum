"""particle.py - rain, snow and wind particles (VFX teammate's code).
Each function makes a manager that spawns particles and recycles them instead of deleting them.
weather.py changes the settings (manager.intensity, .windspeed, ...) while the app runs;
additions for that are marked "sim:".
"""

from ursina import *

import random
import math


class ParticleManager(Entity):
    """sim: the spawning and recycling the three managers share."""

    def __init__(self, intensity, size, life, spawn_point=None, ground=None, max_particles=None):
        super().__init__()
        self.intensity = intensity
        self.size = size
        self.life = life
        self.spawn_point = spawn_point      # () -> (x, y, z) or None (= don't spawn now)
        self.ground = ground                # (x, z) -> height of the terrain there
        self.max_particles = max_particles
        self.timer = 0.1
        self.active = 0
        self.pool = []                      # switched-off particles, ready to reuse

    @property
    def spawnNum(self):
        return int(self.size[0] * self.size[1] * self.intensity / 200)

    @property
    def spawnMax(self):
        n = int(self.spawnNum * self.life / 0.1)
        return n if self.max_particles is None else min(n, self.max_particles)

    def start_position(self):
        raise NotImplementedError

    def new_position(self):
        return self.spawn_point() if self.spawn_point else self.start_position()

    def recycle(self, particle):
        """A particle's life ran out (or it landed): start it again, or switch it off if
        there are more particles than the current intensity needs."""
        position = self.new_position() if self.active <= self.spawnMax else None
        if position is None:
            particle.enabled = False
            self.active -= 1
            self.pool.append(particle)
            return
        particle.position = position
        particle.lifetime = particle.maxlife
        particle.restart()

    def update(self):
        if self.intensity > 0.05 and self.active < self.spawnMax:
            self.timer -= time.dt  # timer creation
            if self.timer <= 0:
                for i in range(min(self.spawnNum, self.spawnMax - self.active)):
                    position = self.new_position()
                    if position is None:
                        break                           # nowhere suitable right now
                    if self.pool:                   # reuse a switched-off particle
                        particle = self.pool.pop()
                        particle.position = position
                        particle.lifetime = particle.maxlife
                        particle.restart()
                        particle.enabled = True
                    else:
                        self.make_particle(position)
                    self.active += 1
                self.timer = 0.1


def rain(intensity = 0.0, center = (0, 0), size = (255, 255), life = 5, height = 5, windspeed = 0, windangle = 0,
         spawn_point = None, ground = None, max_particles = None):
    class RainParticle(Entity):
        def __init__(self, manager, position=(0,0,0), lifetime = 5.0):
            # gives the look of rain
            self.manager = manager
            self.initPos = position

            super().__init__(
                parent=manager,
                model='quad',
                color=color.rgba32(0, 0, 255, 120),
                scale=(0.05, 0.5, 0.05), # scale is stretched out on the y axis to imitate slits of rain
                position=self.initPos,
                double_sided=True,
            )
            self.jitter = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05))
            self.maxlife = lifetime
            self.lifetime = self.maxlife

        def restart(self):
            pass

        def update(self):
            m = self.manager
            # Random trajectory velocity (sim: the wind is read from the manager, so it can change)
            self.velocity = Vec3(
                self.jitter[0] - m.windspeed*0.2*math.cos(m.windangle),
                -5,
                self.jitter[1] - m.windspeed*0.2*math.sin(m.windangle)
            )
            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt

            # Count down life and recycle the particle (sim: also when it hits the ground)
            self.lifetime -= time.dt
            landed = m.ground is not None and self.y <= m.ground(self.x, self.z)
            if self.lifetime <= 0 or self.scale.x <= 0 or landed:
                m.recycle(self)

    class RainManager(ParticleManager):
        def __init__(self):
            super().__init__(intensity, size, life, spawn_point, ground, max_particles)
            self.center = center
            self.height = height
            self.windspeed = windspeed
            self.windangle = windangle

        def start_position(self):
            return (random.uniform(self.center[0]-self.size[0], self.center[0]+self.size[0]), # random based on the size and center tuple
                    self.height,
                    random.uniform(self.center[1]-self.size[1], self.center[1]+self.size[1]))

        def make_particle(self, position):
            return RainParticle(self, position=position, lifetime=self.life)

    return RainManager()

def snow(intensity = 0.0, center = (0, 0), size = (255, 255), life = 15, height = 15, windspeed = 0, windangle = 0,
         spawn_point = None, ground = None, max_particles = None):

    class SnowParticle(Entity):
        def __init__(self, manager, position=(0,0,0), lifetime = 5.0):
            self.manager = manager
            self.initPos = position

            # gives the look of snow
            super().__init__(
                parent=manager,
                model='quad',
                color=color.rgba32(255, 255, 255, 150),
                rotation=Vec3(0, 0, random.uniform(0, 360)),
                scale=(0.07, 0.07, 0.07),
                position=self.initPos,
                double_sided=True,
                billboard=True  # Keeps particles facing the camera
            )
            self.jitter = (random.uniform(-0.05, 0.05), random.uniform(-0.05, 0.05))
            self.sway = 0.0
            self.maxlife = lifetime
            self.lifetime = self.maxlife  # seconds

        def restart(self):
            self.sway = 0.0

        def update(self):
            m = self.manager
            self.rotation += Vec3(0, 0, 1)  # Rotate the snowflake
            self.sway += math.sin(time.dt) * 0.01  # Add a slight sway to the snowflake's movement

            # Random trajectory velocity (sim: the wind is read from the manager, so it can change)
            self.velocity = Vec3(
                self.jitter[0] + self.sway - m.windspeed*0.2*math.cos(m.windangle),
                -1,
                self.jitter[1] - m.windspeed*0.2*math.sin(m.windangle)
            )
            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt

            # Count down life and recycle the particle (sim: also when it hits the ground)
            self.lifetime -= time.dt
            landed = m.ground is not None and self.y <= m.ground(self.x, self.z)
            if self.lifetime <= 0 or landed:
                m.recycle(self)

    class SnowManager(ParticleManager):
        def __init__(self):
            super().__init__(intensity, size, life, spawn_point, ground, max_particles)
            self.center = center
            self.height = height
            self.windspeed = windspeed
            self.windangle = windangle

        def start_position(self):
            return (random.uniform(self.center[0]-self.size[0], self.center[0]+self.size[0]), # random based on the size and center tuple
                    self.height,
                    random.uniform(self.center[1]-self.size[1], self.center[1]+self.size[1]))

        def make_particle(self, position):
            return SnowParticle(self, position=position, lifetime=self.life)

    return SnowManager()

def wind(intensity = 0.0, speed = 5, size = (255, 20), angle = 0,
         distance = 255 * math.sqrt(2), height = 0, max_particles = None):
    class WindParticle(Entity):
        # gives the look of wind
        def __init__(self, manager, position=(0,0,0)):
            self.manager = manager
            self.initPos = position

            super().__init__(
                parent=manager,
                model='quad',
                color=color.white,
                rotation=(0, -manager.angle, 0), # rotation is an argument so it can be controlled where the wind is blowing
                scale=(0.5, 0.05, 0.05),
                double_sided=True,
                position=self.initPos
            )
            self.restart()

        def restart(self):
            m = self.manager
            self.rotation = (0, -m.angle, 0)    # sim: follow the manager's current wind direction
            # Random trajectory velocity
            self.velocity = Vec3(
                -random.uniform(m.speed, m.speed*1.5)*math.cos(math.radians(-self.rotation.y)) + math.sin(time.dt*0.01),
                0,
                -random.uniform(m.speed, m.speed*1.5)*math.sin(math.radians(-self.rotation.y)) + math.sin(time.dt*0.01)
            )
            self.maxlife = 2 * m.distance / m.speed   # long enough to cross the map
            self.lifetime = self.maxlife  # seconds

        def update(self):

            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt

            self.scale_x += sin(time.dt * 0.01) * 0.1  # Oscillate the scale for a waving effect

            # Count down life and recycle the particle
            self.lifetime -= time.dt
            if self.lifetime <= 0 or self.scale_x <= 0:
                self.manager.recycle(self)

    class WindManager(ParticleManager):
        def __init__(self):
            super().__init__(intensity, size, 2 * distance / speed, None, None, max_particles)
            self.speed = speed
            self.angle = angle
            self.distance = distance
            self.height = height

        def start_position(self):
            """Uses trig to pick the side of the map the wind starts on, spread out across it."""
            self.life = 2 * self.distance / self.speed
            a = self.angle
            return (self.distance*math.cos(math.radians(a)) + random.uniform(-self.size[0], self.size[0])*math.cos(math.radians(a + 90)),
                    self.height + random.uniform(-self.size[1], self.size[1]),
                    self.distance*math.sin(math.radians(a)) + random.uniform(-self.size[0], self.size[0])*math.sin(math.radians(a + 90)))

        def make_particle(self, position):
            return WindParticle(self, position=position)

    return WindManager()
