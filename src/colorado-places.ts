/** Labelled place dots and river names for the Colorado crown, read from the package manifest.
 *  Positions are baked through the same display warp as the terrain, so each label sits on its own ground. */
import { Vec3 } from 'playcanvas';
import type { CameraComponent } from 'playcanvas';
import { SPHERE_CENTRE } from './colorado-atmosphere';

type Mark = { name: string; model_xyz: [number, number, number] };

/** Builds the label layer; call the returned function each frame. */
export async function createPlaces(root: string, layer: HTMLElement): Promise<(camera: CameraComponent, eye: Vec3) => void> {
  const manifest = await (await fetch(`${root}/manifest.json`)).json() as { places?: Mark[]; river_labels?: Mark[] };
  const make = (mark: Mark, kind: 'town' | 'river') => {
    const [x, y, z] = mark.model_xyz;
    const world = new Vec3(x, z + .004, -y);  // source Z-up to GLB Y-up, lifted just clear of the surface
    const element = document.createElement('div'); element.className = `place ${kind}`;
    element.innerHTML = kind === 'town' ? '<span class="dot"></span><span class="name"></span>' : '<span class="name"></span>';
    element.querySelector('.name')!.textContent = kind === 'river' ? mark.name.replace(/ River$/, '') : mark.name;
    layer.appendChild(element);
    return { world, normal: world.clone().sub(SPHERE_CENTRE).normalize(), element };
  };
  const marks = [...(manifest.places ?? []).map(m => make(m, 'town')), ...(manifest.river_labels ?? []).map(m => make(m, 'river'))];
  const screen = new Vec3(), view = new Vec3();
  return (camera, eye) => {
    for (const mark of marks) {
      // Hide marks on the far side of the globe; near the limb they fade out.
      const facing = view.sub2(eye, mark.world).normalize().dot(mark.normal);
      camera.worldToScreen(mark.world, screen);
      const visible = facing > .05 && screen.z > 0;
      mark.element.style.opacity = visible ? String(Math.min(1, (facing - .05) * 8)) : '0';
      mark.element.style.transform = `translate(${screen.x}px, ${screen.y}px)`;
    }
  };
}
