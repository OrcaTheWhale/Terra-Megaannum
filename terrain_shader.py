"""terrain_shader.py - colours the terrain on the graphics card: grass, dirt, rock on steep
slopes, plants from vegetation.py, snow above the snow line; and the water shader (ice above it).
"""

from ursina import Shader

terrain_shader = Shader(
    name="terrain_blend",
    language=Shader.GLSL,
    vertex="""
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform float height_ratio;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;

out vec2 terrain_uv;
out vec2 map_uv;
out float elevation;
out float steepness;
out vec3 normal;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    map_uv = p3d_MultiTexCoord0;               // 0-1 across the whole map (for the plant map)
    terrain_uv = p3d_MultiTexCoord0 * 8.0;
    elevation = p3d_Vertex.y;                 // 0 = lowest point, 1 = highest

    normal = normalize(p3d_Normal);
    // the real slope: squash the normal by how much taller the model is drawn than reality
    vec3 real_normal = normalize(vec3(normal.x * height_ratio, normal.y, normal.z * height_ratio));
    steepness = 1.0 - abs(real_normal.y);     // 0 = flat; 0.08 is about 23 degrees, 0.25 about 41
}
""",
    fragment="""
#version 140
uniform sampler2D grass_tex;
uniform sampler2D rock_tex;
uniform sampler2D dirt_tex;
uniform sampler2D snow_tex;
uniform sampler2D dirt_tex;
uniform sampler2D veg_tex;
uniform float veg_on;
uniform float snow_line;

in vec2 terrain_uv;
in vec2 map_uv;
in float elevation;
in float steepness;
in vec3 normal;

out vec4 fragColor;

void main() {
    vec4 grass = texture(grass_tex, terrain_uv);
    vec4 rock = texture(rock_tex, terrain_uv);
    vec4 snow = texture(snow_tex, terrain_uv);
    vec4 dirt = texture(dirt_tex, terrain_uv);

<<<<<<< HEAD
    // teammate's ground: dirt on low ground and on moderate slopes, rock on steep ones
=======
>>>>>>> 6f462d55238ad6b8f075802de15a3d4c03da83a4
    float lowland_dirt = 0.55 * (1.0 - smoothstep(0.2, 0.65, elevation));
    float slope_dirt = smoothstep(0.04, 0.09, steepness)
                     * (1.0 - smoothstep(0.15, 0.21, steepness));
    float dirt_amount = max(lowland_dirt, slope_dirt);
    float rock_amount = smoothstep(0.18, 0.3, steepness);
    // snow fades in just above the 0 C height; steep rock holds less snow
    float snow_amount = smoothstep(snow_line, snow_line + 0.06, elevation) * (1.0 - 0.6 * rock_amount);

<<<<<<< HEAD
    vec4 grassland = mix(grass, dirt, dirt_amount);
    vec4 ground;
    if (veg_on > 0.5) {
        // plants (vegetation.py): bare dirt -> the teammate's grassland -> dark forest
        float veg = texture(veg_tex, map_uv).r;
        vec4 forest = vec4(grass.rgb * vec3(0.5, 0.68, 0.45), 1.0);
        vec4 plants = mix(grassland, forest, smoothstep(0.6, 0.95, veg));
        ground = mix(dirt, plants, smoothstep(0.05, 0.45, veg));
    } else {
        ground = grassland;                    // Vegetation off: exactly the teammate's look
    }
=======
    vec4 ground = mix(grass, dirt, dirt_amount);
>>>>>>> 6f462d55238ad6b8f075802de15a3d4c03da83a4
    ground = mix(ground, rock, rock_amount);
    vec4 colour = mix(ground, snow, snow_amount);

    // simple sunlight: slopes facing the sun are brighter
    vec3 sun = normalize(vec3(0.4, 1.0, -0.3));
    float light = 0.55 + 0.45 * max(dot(normalize(normal), sun), 0.0);
    fragColor = vec4(colour.rgb * light, 1.0);
}
""")


# ---------------------------------------------------------------- water and ice
# The water surface (water.py) uses this: rippling blue water below the 0 C height, ice above it.
# freeze_line is the same 0-1 height as the snow line, so lakes high in the mountains freeze
# first, and with Day / Season steps lakes freeze in winter and thaw in spring.
water_shader = Shader(
    name="water_ice",
    language=Shader.GLSL,
    vertex="""
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;
out vec2 uv;
out float elevation;
out vec3 normal;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
    elevation = p3d_Vertex.y;                 // 0 = lowest point, 1 = highest
    normal = normalize(p3d_Normal);
}
""",
    fragment="""
#version 140
uniform sampler2D p3d_Texture0;               // the rippling water texture
uniform float freeze_line;
in vec2 uv;
in float elevation;
in vec3 normal;
out vec4 fragColor;

void main() {
    vec4 water = texture(p3d_Texture0, uv * 6.0);
    // ice: pale blue-white, with a faint pattern from the ripples so it isn't flat
    vec3 ice = vec3(0.82, 0.90, 0.96) + 0.08 * (water.rgb - vec3(0.15, 0.5, 0.75));
    float frozen = smoothstep(freeze_line, freeze_line + 0.02, elevation);
    vec3 colour = mix(water.rgb, ice, frozen);
    vec3 sun = normalize(vec3(0.4, 1.0, -0.3));
    float light = 0.75 + 0.25 * max(dot(normalize(normal), sun), 0.0);
    fragColor = vec4(colour * light, 1.0);
}
""")
