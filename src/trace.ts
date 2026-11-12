export interface TraceResult {
  valid: boolean;
  reasons: string[];
  frames: number;
  durationMs: number;
  fps: number;
  p95Ms: number;
  within16_7Percent: number;
  peakDraws: number;
  peakGpuBytes: number;
  frameTimesMs: number[];
}

export class FrameTrace {
  private duration: number;
  private start: number | null = null;
  private previous = 0;
  private samples: number[] = [];
  private reasons = new Set<string>();
  private peakDraws = 0;
  private peakGpuBytes = 0;
  constructor(duration = 60000) { this.duration = duration; }
  add(timestamp: number, draws: number, gpuBytes: number): TraceResult | null {
    this.peakDraws = Math.max(draws, this.peakDraws);
    this.peakGpuBytes = Math.max(gpuBytes, this.peakGpuBytes);
    if (this.start === null) {
      this.start = this.previous = timestamp;
      return null;
    }
    this.samples.push(timestamp-this.previous);
    this.previous = timestamp;
    const durationMs = timestamp-this.start;
    if (durationMs < this.duration) return null;
    const sorted = [...this.samples].sort((a,b) => a-b);
    return { valid: this.reasons.size===0, reasons: [...this.reasons],
      frames: sorted.length, durationMs, fps: sorted.length*1000/durationMs,
      p95Ms: sorted[Math.ceil(sorted.length*.95)-1],
      within16_7Percent: sorted.filter(time => time<=16.7).length/sorted.length*100,
      peakDraws: this.peakDraws, peakGpuBytes: this.peakGpuBytes,
      frameTimesMs: [...this.samples] };
  }
  invalidate(reason: string) { this.reasons.add(reason); }
}
