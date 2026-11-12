/** Orbit state in metres/radians, independent of the rendering engine. */
export class Orbit {
  yaw = .62;
  pitch = .65;
  distance: number;
  x = 0;
  z = 0;
  readonly size: number;
  height: number;
  private aspectFactor = 1;
  constructor(size: number, height: number, aspect = 16/9) {
    this.size = size;
    this.height = height;
    this.distance = size*1.45;
    this.resize(aspect);
  }
  get maxDistance() { return this.size*2.5*this.aspectFactor; }
  resize(aspect: number) {
    const factor = Math.max(1,1.5/Math.max(aspect,.1));
    this.distance *= factor/this.aspectFactor;
    this.aspectFactor = factor;
  }
  rotate(dx: number, dy: number) {
    this.yaw -= dx*.005;
    this.pitch = Math.max(.35, Math.min(1.2, this.pitch+dy*.005));
  }
  zoom(delta: number) {
    this.distance = Math.max(this.size*.015, Math.min(this.maxDistance,
      this.distance*Math.exp(Math.max(-1, Math.min(1, delta*.001)))));
  }
  pan(dx: number, dy: number) {
    const scale = this.distance*.001;
    this.x = Math.max(-this.size/2, Math.min(this.size/2,
      this.x+(-dx*Math.cos(this.yaw)+dy*Math.sin(this.yaw))*scale));
    this.z = Math.max(-this.size/2, Math.min(this.size/2,
      this.z+(dx*Math.sin(this.yaw)+dy*Math.cos(this.yaw))*scale));
  }
  get eye(): [number, number, number] {
    const horizontal = Math.cos(this.pitch)*this.distance;
    return [this.x+Math.sin(this.yaw)*horizontal,
      this.height+Math.sin(this.pitch)*this.distance,
      this.z+Math.cos(this.yaw)*horizontal];
  }
}
