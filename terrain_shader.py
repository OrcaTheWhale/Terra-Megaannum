"""
terrain_shader.py - paints the terrain on the graphics card: grass, rock on steep slopes,
snow above the snow line, with simple sunlight shading.

Inputs set from Python (main.py):
    grass_tex, rock_tex, snow_tex   the three textures
    snow_line                       height (0 = lowest point, 1 = highest) where it's 0 C;
                                    worked out from the climate, so warming melts the snow
    height_ratio                    real height range / real map width (e.g. 1500 m / 10000 m),
                                    so rock goes on slopes that are really steep (~25-40 degrees),
                                    not ones that only look steep because the 3D view is stretched
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
out float elevation;
out float steepness;
out vec3 normal;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

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
uniform sampler2D snow_tex;
uniform float snow_line;

in vec2 terrain_uv;
in float elevation;
in float steepness;
in vec3 normal;

out vec4 fragColor;

void main() {
    vec4 grass = texture(grass_tex, terrain_uv);
    vec4 rock = texture(rock_tex, terrain_uv);
    vec4 snow = texture(snow_tex, terrain_uv);

    float rock_amount = smoothstep(0.08, 0.25, steepness);
    // snow fades in just above the 0 C height; steep rock holds less snow
    float snow_amount = smoothstep(snow_line, snow_line + 0.06, elevation) * (1.0 - 0.6 * rock_amount);

    vec4 ground = mix(grass, rock, rock_amount);
    vec4 colour = mix(ground, snow, snow_amount);

    // simple sunlight: slopes facing the sun are brighter
    vec3 sun = normalize(vec3(0.4, 1.0, -0.3));
    float light = 0.55 + 0.45 * max(dot(normalize(normal), sun), 0.0);
    fragColor = vec4(colour.rgb * light, 1.0);
}
""")
