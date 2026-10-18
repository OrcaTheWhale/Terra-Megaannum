from ursina import *

import random
import math

def rain(intensity = 0.0, center = (0, 0), size = (255, 255), life = 5, height = 5, windspeed = 5, windangle = 0):
    class RainParticle(Entity):
        def __init__(self, position=(0,0,0), lifetime = 5.0):
            # gives the look of rain
            self.initPos = position

            super().__init__(
                model='quad',
                color=color.rgba(0, 0, 255, 120),
                scale=(0.05, 0.5, 0.05), # scale is stretched out on the y axis to imitate slits of rain
                position=self.initPos,
                double_sided=True,
                billboard=True  # Keeps particles facing the camera
            )
            # Random trajectory velocity
            self.velocity = Vec3(
                random.uniform(-0.05, 0.05) - windspeed*0.2*math.cos(windangle),
                -5,
                random.uniform(-0.05, 0.05) - windspeed*0.2*math.sin(windangle)
            )

            self.maxlife = lifetime
            self.lifetime = self.maxlife
            
        def update(self):
            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt
            
            # Count down life and destroy entity
            self.lifetime -= time.dt
            if self.lifetime <= 0 or self.scale.x <= 0:
                self.position=self.initPos
                self.lifetime = self.maxlife

    class RainManager(Entity):
        def __init__(self):
            super().__init__()
            self.num = 0
            self.timer = 0.1
            self.spawnNum = int(size[0] * size[1] * intensity / 200)
            self.spawnMax = int(self.spawnNum * life / self.timer) 

        def update(self):
            if intensity > 0.05 and self.num < self.spawnMax:
                self.timer -= time.dt # timer creation
    
                if self.timer <= 0:
                    for i in range(self.spawnNum): # generates rain, how much dependent on 
                        RainParticle(
                            position=(
                                random.uniform(center[0]-size[0], center[0]+size[0]), # random based on the size and center tuple 
                                height, 
                                random.uniform(center[1]-size[1], center[1]+size[1])
                                ),
                            lifetime = life
                            )
                    self.num += self.spawnNum   
                    self.timer = 0.1

    return RainManager()

def snow(intensity = 0.0, center = (0, 0), size = (255, 255), life = 15, height = 15, windspeed = 5, windangle = 0):

    class SnowParticle(Entity):
        def __init__(self, position=(0,0,0), lifetime = 5.0):
            self.initPos = position

            # gives the look of snow
            super().__init__(
                model='quad',
                color=color.rgba(255, 255, 255, 150),
                rotation=Vec3(0, 0, random.uniform(0, 360)),
                scale=(0.07, 0.07, 0.07),
                position=self.initPos,
                double_sided=True,
                billboard=True  # Keeps particles facing the camera
            )

            # Random trajectory velocity
            self.velocity = Vec3(
                random.uniform(-0.05, 0.05) - windspeed*0.2*math.cos(windangle),
                -1,
                random.uniform(-0.05, 0.05) - windspeed*0.2*math.sin(windangle)
            )
            self.maxlife = lifetime
            self.lifetime = self.maxlife  # seconds
            
        def update(self):
            self.rotation += Vec3(0, 0, 1)  # Rotate the snowflake
            self.velocity += Vec3(math.sin(time.dt) * 0.01, 0, 0)  # Add a slight sway to the snowflake's movement
            
            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt
            
            # Count down life and destroy entity
            self.lifetime -= time.dt
            if self.lifetime <= 0:
                self.position = self.initPos
                self.lifetime = self.maxlife
        
    class SnowManager(Entity):
        def __init__(self):
            super().__init__()
            self.num = 0
            self.timer = 0.1
            self.spawnNum = int(size[0] * size[1] * intensity / 200)
            self.spawnMax = int(self.spawnNum * life / self.timer) 

        def update(self):
            if intensity > 0.05 and self.num < self.spawnMax:
                self.timer -= time.dt # timer creation
    
                if self.timer <= 0:
                    for i in range(self.spawnNum): # generates rain, how much dependent on 
                        SnowParticle(
                            position=(
                                random.uniform(center[0]-size[0], center[0]+size[0]), # random based on the size and center tuple 
                                height, 
                                random.uniform(center[1]-size[1], center[1]+size[1])
                                ),
                            lifetime = life
                            )
                    self.num += self.spawnNum   
                    self.timer = 0.1
    
    return SnowManager()

def wind(intensity = 0.0, speed = 5, size = (255, 20), angle = 0):
    class WindParticle(Entity):
        # gives the look of wind 
        def __init__(self, position=(0,0,0), rotation=(0,0,0)):
            self.initPos = position

            super().__init__(
                model='quad',
                color=color.white,
                rotation=rotation, # rotation is an argument so it can be controlled where the wind is blowing
                scale=(0.5, 0.05, 0.05),
                double_sided=True,
                position=self.initPos
            )

            # Random trajectory velocity
            self.velocity = Vec3(
                -random.uniform(speed, speed*1.5)*math.cos(math.radians(-self.rotation.y)) + math.sin(time.dt*0.01), 
                0, 
                -random.uniform(speed, speed*1.5)*math.sin(math.radians(-self.rotation.y)) + math.sin(time.dt*0.01)
            )
            
            self.maxLife = 255 * 2 * math.sqrt(2) / speed # 255 is map size
            self.lifetime = self.maxLife  # seconds
            
        def update(self):
            
            # Move particle based on velocity and delta time
            self.position += self.velocity * time.dt

            self.scale.x += sin(time.dt * 0.01) * 0.1  # Oscillate the scale for a waving effect
            
            # Count down life and destroy entity
            self.lifetime -= time.dt
            if self.lifetime <= 0 or self.scale.x <= 0:
                self.position = self.initPos
                self.lifetime = self.maxLife

    class WindManager(Entity):
        def __init__(self):
            super().__init__()
            self.num = 0
            self.timer = 0.1
            self.life = 255 * 2 * math.sqrt(2) / speed
            self.spawnNum = int(size[0] * size[1] * intensity / 200)
            self.spawnMax = int(self.spawnNum * self.life / self.timer) 

        def update(self):
            if intensity > 0.05 and self.num < self.spawnMax:
            
                self.timer -= time.dt # timer
                
                if self.timer <= 0:
                    for i in range(self.spawnNum):
                        """
                        the below lines are difficult to explain 
                        but they use trig to determine on what side the map spawns 
                        and randomizes the placement on a plane perpendicular to the direction
                        """
                        WindParticle(
                            position=(
                                255*math.sqrt(2)*math.cos(math.radians(angle)) + random.uniform(-size[0], size[0])*math.cos(math.radians(angle + 90)), 
                                random.uniform(-size[1], size[1]),
                                255*math.sqrt(2)*math.sin(math.radians(angle)) + random.uniform(-size[0], size[0])*math.sin(math.radians(angle + 90))
                            ), 
                            rotation=(0, -angle, 0),
                        )
                    self.num += self.spawnNum
                    self.spawnT = 0.1

    return WindManager()

    