export type RobotState = {
  battery: number;
  latencyMs: number;
  fps: number;
  workStatus: string;
  pose: { x: number; y: number; yaw: number };
  head: { pan: number; tilt: number };
  base: { speed: number };
  network?: { wifiStrength?: number; downloadRate?: string };
};

export type VisionTarget = {
  id: string;
  label: string;
  bbox: [number, number, number, number];
  score: number;
};

export type LogEntry = { ts: string; level: string; message: string };
