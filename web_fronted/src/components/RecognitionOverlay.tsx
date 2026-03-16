'use client';

import { VisionTarget } from './types';

type Props = {
  enabled: boolean;
  targets: VisionTarget[];
  selectedId?: string;
  onSelect: (targetId: string) => void;
};

export default function RecognitionOverlay({ enabled, targets, selectedId, onSelect }: Props) {
  if (!enabled) return null;

  return (
    <>
      {targets.map((target) => {
        const [x1, y1, x2, y2] = target.bbox;
        return (
          <div
            key={target.id}
            className={`overlay-box ${selectedId === target.id ? 'selected' : ''}`}
            style={{ left: x1, top: y1, width: x2 - x1, height: y2 - y1 }}
            onClick={() => onSelect(target.id)}
            title={`${target.label} (${target.score})`}
          >
            {target.label} {Math.round(target.score * 100)}%
          </div>
        );
      })}
    </>
  );
}
