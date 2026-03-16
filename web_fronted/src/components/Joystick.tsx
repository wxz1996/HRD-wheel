'use client';

import { useRef, useState } from 'react';

type Props = {
  onChange: (x: number, y: number) => void;
};

const RADIUS = 90;
const KNOB_HALF = 31;
const DEADZONE = 0.15;

export default function Joystick({ onChange }: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });

  const updateByEvent = (clientX: number, clientY: number) => {
    if (!areaRef.current) return;
    const rect = areaRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = clientX - cx;
    const dy = clientY - cy;
    const dist = Math.min(Math.sqrt(dx * dx + dy * dy), RADIUS - KNOB_HALF);
    const angle = Math.atan2(dy, dx);
    const nx = dist * Math.cos(angle);
    const ny = dist * Math.sin(angle);
    setPos({ x: nx, y: ny });

    let ox = nx / (RADIUS - KNOB_HALF);
    let oy = ny / (RADIUS - KNOB_HALF);
    if (Math.abs(ox) < DEADZONE) ox = 0;
    if (Math.abs(oy) < DEADZONE) oy = 0;
    onChange(Number(ox.toFixed(2)), Number((-oy).toFixed(2)));
  };

  const reset = () => {
    setPos({ x: 0, y: 0 });
    onChange(0, 0);
  };

  return (
    <div
      ref={areaRef}
      className="joystick"
      onPointerDown={(e) => {
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        updateByEvent(e.clientX, e.clientY);
      }}
      onPointerMove={(e) => e.buttons === 1 && updateByEvent(e.clientX, e.clientY)}
      onPointerUp={reset}
      onPointerCancel={reset}
    >
      <div className="knob" style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }} />
    </div>
  );
}
