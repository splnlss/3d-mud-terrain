/** Scene presentation for the Colorado crown: an atmosphere halo behind the globe and a small, terrain-occluded sunrise.
 *  Nothing here touches the portable GLB; the Blender review scene reproduces the same formula. */
import { BLEND_ADDITIVE, CULLFACE_NONE, Color, Entity, SEMANTIC_POSITION, ShaderMaterial, StandardMaterial, Vec3 } from 'playcanvas';

/** Sphere centre and sun in GLB axes (Y up, north -Z); cap half-angle matches colorado_globe.CAP_ANGLE. */
const CAP_ANGLE = 46 * Math.PI / 180, SPHERE = .8 / Math.sin(CAP_ANGLE);
export const SPHERE_CENTRE = new Vec3(0, -SPHERE * Math.cos(CAP_ANGLE), 0);
export const SUN_POSITION = new Vec3(.30, .44, -1.7);
export const HALO_REACH = SPHERE * 1.7, GLOW = 1.2, HALO = 3.0;

// A camera-facing quad one sphere radius behind the globe centre; the terrain in front of it hides everything but the rim.
const vertex = `
attribute vec3 aPosition;
uniform mat4 matrix_viewProjection; uniform vec3 uOrigin; uniform vec3 uRight; uniform vec3 uUp; uniform float uScale;
varying vec2 vLocal; varying float vHeight;
void main(void) {
  vLocal = aPosition.xz * ${(HALO_REACH * 2.1).toFixed(4)};
  vec3 world = uOrigin + (uRight * vLocal.x + uUp * vLocal.y) * uScale; vHeight = world.y;
  gl_Position = matrix_viewProjection * vec4(world, 1.0);
}`;
// Pale cool glow brightest at the limb with a cubic fade outward; amber toward the sun; nothing near the ground ring.
const fragment = `
uniform vec2 uSun;
varying vec2 vLocal; varying float vHeight;
void main(void) {
  float r = length(vLocal);
  float profile = pow(clamp((${HALO_REACH.toFixed(4)} - r) / ${(HALO_REACH - SPHERE * .97).toFixed(4)}, 0.0, 1.0), 3.0);
  float gate = smoothstep(.0, .45, vHeight);
  float warm = pow(max(dot(vLocal / max(r, 1e-4), uSun), 0.0), 24.0);
  gl_FragColor = vec4((vec3(.45, .66, 1.0) * ${(GLOW * 1.6).toFixed(2)} + vec3(1.0, .55, .22) * warm * ${HALO.toFixed(2)}) * profile * gate, 1.0);
}`;

/** Adds the halo, sun and back light; call the returned function each frame with the camera position. */
export function createAtmosphere(root: Entity): (eye: Vec3) => void {
  const material = new ShaderMaterial({ uniqueName: 'colorado-atmosphere', vertexGLSL: vertex, fragmentGLSL: fragment, attributes: { aPosition: SEMANTIC_POSITION } });
  material.blendType = BLEND_ADDITIVE; material.depthWrite = false; material.cull = CULLFACE_NONE;
  material.update();
  const halo = new Entity('atmosphere halo'); halo.addComponent('render', { type: 'plane', castShadows: false, receiveShadows: false, material });
  halo.render!.meshInstances.forEach(instance => { instance.cull = false; });
  const glowing = new StandardMaterial(); glowing.diffuse = new Color(0, 0, 0); glowing.emissive = new Color(1, .62, .3); glowing.emissiveIntensity = 1.5; glowing.update();
  const sun = new Entity('sun'); sun.addComponent('render', { type: 'sphere', castShadows: false, material: glowing }); sun.setLocalScale(.05, .05, .05); sun.setPosition(SUN_POSITION);
  const backlight = new Entity('warm back light'); backlight.addComponent('light', { type: 'directional', color: new Color(1, .72, .45), intensity: .5, castShadows: false });
  backlight.setPosition(SUN_POSITION); backlight.lookAt(0, .3, 0);
  for (const entity of [halo, sun, backlight]) root.addChild(entity);
  const sunDir = SUN_POSITION.clone().sub(SPHERE_CENTRE).normalize(), away = new Vec3(), right = new Vec3(), up = new Vec3(), origin = new Vec3();
  return eye => {
    away.sub2(SPHERE_CENTRE, eye); const distance = away.length(); away.normalize();
    right.cross(away, Vec3.UP).normalize(); up.cross(right, away).normalize(); origin.copy(away).mulScalar(SPHERE).add(SPHERE_CENTRE);
    material.setParameter('uOrigin', [origin.x, origin.y, origin.z]); material.setParameter('uRight', [right.x, right.y, right.z]); material.setParameter('uUp', [up.x, up.y, up.z]);
    material.setParameter('uScale', (distance + SPHERE) / distance);
    const sx = sunDir.dot(right), sy = sunDir.dot(up), length = Math.hypot(sx, sy) || 1; material.setParameter('uSun', [sx / length, sy / length]);
  };
}
