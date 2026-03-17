'use client';

import { useEffect, useState } from 'react';
import RecognitionOverlay from './RecognitionOverlay';
import { VisionTarget } from './types';

type Props = {
  recognitionEnabled: boolean;
  targets: VisionTarget[];
  selectedId?: string;
  onSelect: (targetId: string) => void;
  streamUrl: string;
};

export default function VideoPanel({ recognitionEnabled, targets, selectedId, onSelect, streamUrl }: Props) {
  const [streamReady, setStreamReady] = useState(false);
  const [streamError, setStreamError] = useState('');

  useEffect(() => {
    setStreamReady(false);
    setStreamError('');
  }, [streamUrl]);

  return (
    <div className="video-panel card">
      {streamUrl ? (
        <img
          src={streamUrl}
          alt="robot rgb stream"
          onLoad={() => {
            setStreamReady(true);
            setStreamError('');
          }}
          onError={() => {
            setStreamReady(false);
            setStreamError('视频流不可用，请检查机器人端 RealSense/MQTT 链路');
          }}
        />
      ) : null}
      {!streamReady && !streamError && <div className="video-overlay-hint">等待机器人 RGB 视频流...</div>}
      {streamError && <div className="video-overlay-hint">{streamError}</div>}
      <RecognitionOverlay
        enabled={recognitionEnabled}
        targets={targets}
        selectedId={selectedId}
        onSelect={onSelect}
      />
    </div>
  );
}
