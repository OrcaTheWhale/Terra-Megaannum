from ursina import Shader

terrain_shader = Shader(
    name="terrain_blend",
    language=Shader.GLSL,
    vertex="""
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;

in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
in vec3 p3d_Normal;

out vec2 terrain_uv;
out float elevation;
out float steepness;

void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;

    terrain_uv = p3d_MultiTexCoord0 * 8.0;
    elevation = p3d_Vertex.y;

    vec3 normal = normalize(p3d_Normal);
    steepness = 1.0 - abs(normal.y);
}
""",
    fragment="""
#version 140
uniform sampler2D grass_tex;
uniform sampler2D rock_tex;
uniform sampler2D snow_tex;

in vec2 terrain_uv;
in float elevation;
in float steepness;

out vec4 fragColor;

void main() {
    vec4 grass = texture(grass_tex, terrain_uv);
    vec4 rock = texture(rock_tex, terrain_uv);
    vec4 snow = texture(snow_tex, terrain_uv);

    float rock_amount = smoothstep(0.08, 0.25, steepness);
    float snow_amount = smoothstep(0.72, 0.86, elevation);

    vec4 ground = mix(grass, rock, rock_amount);
    fragColor = mix(ground, snow, snow_amount);
}
""")