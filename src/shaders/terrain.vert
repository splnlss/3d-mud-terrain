attribute vec3 aPosition;
attribute vec3 aNormal;
attribute vec3 aColor;
attribute vec2 aUv;
uniform mat4 matrix_model;
uniform mat4 matrix_viewProjection;
uniform mat3 matrix_normal;
varying vec3 vWorld;
varying vec3 vNormal;
varying vec2 vUv;
varying float vAO;
varying float vWet;
void main(void) {
    vec4 world = matrix_model * vec4(aPosition, 1.0);
    vWorld = world.xyz;
    vNormal = normalize(matrix_normal * aNormal);
    vUv = aUv;
    vAO = aColor.r;
    vWet = aColor.g;
    gl_Position = matrix_viewProjection * world;
}
