attribute vec3 aPosition;
uniform mat4 matrix_model;
uniform mat4 matrix_viewProjection;
uniform float uLevel;
varying vec3 vWorld;
void main(void) {
    vec4 world = matrix_model * vec4(aPosition, 1.0);
    world.y += uLevel;
    vWorld = world.xyz;
    gl_Position = matrix_viewProjection * world;
}
