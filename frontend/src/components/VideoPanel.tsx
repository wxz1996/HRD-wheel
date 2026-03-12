import RecognitionOverlay from './RecognitionOverlay';
import { VisionTarget } from './types';

type Props = {
  recognitionEnabled: boolean;
  targets: VisionTarget[];
  selectedId?: string;
  onSelect: (targetId: string) => void;
};

export default function VideoPanel({ recognitionEnabled, targets, selectedId, onSelect }: Props) {
  return (
    <div className="video-panel card">
      <img src="https://images.unsplash.com/photo-1561144257-e32e8efc6c4f?auto=format&fit=crop&w=1280&q=80" alt="mock video" />
      <RecognitionOverlay
        enabled={recognitionEnabled}
        targets={targets}
        selectedId={selectedId}
        onSelect={onSelect}
      />
    </div>
  );
}
