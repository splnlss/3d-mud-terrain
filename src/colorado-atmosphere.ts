/** Scene presentation for the Colorado crown: an atmosphere behind the globe (broad halo plus a thin limb band) and a warm sunrise glow.
 *  Nothing here touches the portable GLB; the Blender review scene reproduces the same formula. */
import { BLEND_ADDITIVE, CULLFACE_NONE, Color, Entity, SEMANTIC_POSITION, ShaderMaterial, Vec3 } from 'playcanvas';

/** Sphere centre and sun in GLB axes (Y up, north -Z); cap half-angle matches colorado_globe.CAP_ANGLE. */
const CAP_ANGLE = 46 * Math.PI / 180, SPHERE = .8 / Math.sin(CAP_ANGLE);
export const SPHERE_CENTRE = new Vec3(0, -SPHERE * Math.cos(CAP_ANGLE), 0);
export const SUN_POSITION = new Vec3(.30, .44, -1.7);
export const HALO_REACH = SPHERE * 1.7, GLOW = 1.2, HALO = 3.0, RIM_WIDTH = .035, RIM = 3.0;

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
// Pale cool glow brightest at the limb with a cubic fade outward, a thin bright band right on the limb, amber toward the sun; nothing near the ground ring.
const fragment = `
uniform vec2 uSun; uniform vec3 uRight; uniform vec3 uUp; uniform float uLimbY; uniform float uLimbRadius;
varying vec2 vLocal; varying float vHeight;
void main(void) {
  float r = length(vLocal);
  float profile = pow(clamp((${HALO_REACH.toFixed(4)} - r) / ${(HALO_REACH - SPHERE * .97).toFixed(4)}, 0.0, 1.0), 3.0);
  float warm = pow(max(dot(vLocal / max(r, 1e-4), uSun), 0.0), 24.0);
  float over = r / ${SPHERE.toFixed(4)} - 1.0;
  float band = exp(-max(over, 0.0) / ${RIM_WIDTH.toFixed(3)}) * step(-.004, over);
  vec2 dir = vLocal / max(r, 1e-4);
  // Height of the sphere's tangent (horizon) point in this direction: the band exists only where the planet's horizon is above ground.
  float horizon = uLimbY + (uRight.y * dir.x + uUp.y * dir.y) * uLimbRadius;
  float arc = smoothstep(.06, .24, horizon);   // strongest high on the planet, gone well before the floor
  // Glow only behind the emerging planet: soft fade toward ground level, and out along the planet's lower sides.
  float gate = smoothstep(.0, .45, vHeight) * smoothstep(.05, .4, horizon);
  gl_FragColor = vec4((vec3(.45, .66, 1.0) * ${(GLOW * 1.6).toFixed(2)} + vec3(1.0, .55, .22) * warm * ${HALO.toFixed(2)}) * profile * gate + vec3(.55, .82, 1.0) * band * arc * ${RIM.toFixed(2)}, 1.0);
}`;

/** Adds the halo and warm back light; call the returned function each frame with the camera position. */
export function createAtmosphere(root: Entity): (eye: Vec3) => void {
  const material = new ShaderMaterial({ uniqueName: 'colorado-atmosphere', vertexGLSL: vertex, fragmentGLSL: fragment, attributes: { aPosition: SEMANTIC_POSITION } });
  material.blendType = BLEND_ADDITIVE; material.depthWrite = false; material.cull = CULLFACE_NONE;
  material.update();
  const halo = new Entity('atmosphere halo'); halo.addComponent('render', { type: 'plane', castShadows: false, receiveShadows: false, material });
  halo.render!.meshInstances.forEach(instance => { instance.cull = false; });
  const backlight = new Entity('warm back light'); backlight.addComponent('light', { type: 'directional', color: new Color(1, .72, .45), intensity: .5, castShadows: false });
  backlight.setPosition(SUN_POSITION); backlight.lookAt(0, .3, 0);
  for (const entity of [halo, backlight]) root.addChild(entity);
  const sunDir = SUN_POSITION.clone().sub(SPHERE_CENTRE).normalize(), away = new Vec3(), right = new Vec3(), up = new Vec3(), origin = new Vec3();
  return eye => {
    away.sub2(SPHERE_CENTRE, eye); const distance = away.length(); away.normalize();
    right.cross(away, Vec3.UP).normalize(); up.cross(right, away).normalize(); origin.copy(away).mulScalar(SPHERE).add(SPHERE_CENTRE);
    material.setParameter('uOrigin', [origin.x, origin.y, origin.z]); material.setParameter('uRight', [right.x, right.y, right.z]); material.setParameter('uUp', [up.x, up.y, up.z]);
    material.setParameter('uScale', (distance + SPHERE) / Math.sqrt(distance * distance - SPHERE * SPHERE));  // exact perspective limb
    // Tangent circle of the sphere seen from the eye: centre moves R²/d toward the eye, radius R·sqrt(1 - R²/d²).
    material.setParameter('uLimbY', SPHERE_CENTRE.y - away.y * SPHERE * SPHERE / distance); material.setParameter('uLimbRadius', SPHERE * Math.sqrt(1 - (SPHERE / distance) ** 2));
    const sx = sunDir.dot(right), sy = sunDir.dot(up), length = Math.hypot(sx, sy) || 1; material.setParameter('uSun', [sx / length, sy / length]);
  };
}
