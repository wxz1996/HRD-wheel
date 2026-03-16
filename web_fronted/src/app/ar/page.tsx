'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Joystick from '@/components/Joystick';
import VideoPanel from '@/components/VideoPanel';
import { LogEntry, RobotState, VisionTarget } from '@/components/types';
import { authHeaders, getApiBase, getAuthToken, getWsBase } from '@/lib/runtime';

const WS_BASE = getWsBase();

export default function ARPage() {
  const router = useRouter();
  const [state, setState] = useState<RobotState>({
    battery: 78,
    latencyMs: 32,
    fps: 28,
    workStatus: '待机中',
    pose: { x: 1.2, y: 0.5, yaw: 0.3 },
    head: { pan: 10, tilt: -5 },
    base: { speed: 0 },
    network: { wifiStrength: 60, downloadRate: '10.2MB/s' },
  });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [targets, setTargets] = useState<VisionTarget[]>([]);
  const [recognitionEnabled, setRecognitionEnabled] = useState(false);
  const [selectedId, setSelectedId] = useState<string>();
  const [streamUrl, setStreamUrl] = useState('');
  const controlWs = useRef<WebSocket | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    const resolveStreamToken = async () => {
      try {
        const resp = await fetch(`${getApiBase()}/api/video/token`, {
          method: 'POST',
          headers: authHeaders(token),
        });
        if (resp.status === 401) {
          localStorage.removeItem('hrt_token');
          router.replace('/login');
          return;
        }
        if (resp.ok) {
          const data = await resp.json();
          if (data?.token) {
            setStreamUrl(`${getApiBase()}/api/video/stream?token=${encodeURIComponent(String(data.token))}`);
            return;
          }
        }
      } catch {
        // Ignore and fallback to bearer token query for compatibility.
      }
      setStreamUrl(`${getApiBase()}/api/video/stream?token=${encodeURIComponent(token)}`);
    };
    void resolveStreamToken();

    fetch(`${getApiBase()}/api/ar/bootstrap`, { headers: authHeaders(token) })
      .then(async (r) => {
        if (r.status === 401) {
          localStorage.removeItem('hrt_token');
          router.replace('/login');
          return null;
        }
        return r.json();
      })
      .then((d) => d && setRecognitionEnabled(d.recognitionEnabled));

    const qs = `?token=${encodeURIComponent(token)}`;
    const handleAuthClose = (evt: CloseEvent) => {
      if (evt.code === 4401) {
        localStorage.removeItem('hrt_token');
        router.replace('/login');
      }
    };

    const wsState = new WebSocket(`${WS_BASE}/state${qs}`);
    wsState.onclose = handleAuthClose;
    wsState.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'state') setState((prev) => ({ ...prev, ...msg.payload }));
    };

    const wsLogs = new WebSocket(`${WS_BASE}/logs${qs}`);
    wsLogs.onclose = handleAuthClose;
    wsLogs.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'log') setLogs((prev) => [...prev.slice(-199), msg.payload]);
    };

    const wsVision = new WebSocket(`${WS_BASE}/vision${qs}`);
    wsVision.onclose = handleAuthClose;
    wsVision.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'vision_results') setTargets(msg.payload.targets);
    };

    const wsControl = new WebSocket(`${WS_BASE}/control${qs}`);
    wsControl.onclose = handleAuthClose;
    wsControl.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === 'control_ack') {
        setLogs((prev) => [...prev.slice(-199), {
          ts: new Date().toISOString(), level: 'INFO', message: `控制ACK: ${msg.payload.source}`,
        }]);
      }
    };
    controlWs.current = wsControl;

    return () => [wsState, wsLogs, wsVision, wsControl].forEach((w) => w.close());
  }, [router]);

  const toggleRecognition = async (enabled: boolean) => {
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    setRecognitionEnabled(enabled);
    await fetch(`${getApiBase()}/api/ar/recognition/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ enabled }),
    });
  };

  const selectTarget = async (targetId: string) => {
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    setSelectedId(targetId);
    await fetch(`${getApiBase()}/api/ar/selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ targetId }),
    });
  };

  const sendJoystick = (x: number, y: number) => {
    const payload = { type: 'base_joystick', payload: { x, y } };
    if (controlWs.current?.readyState === WebSocket.OPEN) {
      controlWs.current.send(JSON.stringify(payload));
    }
  };

  return (
    <main className="ar-layout">
      <div className="topbar">
        <button className="btn secondary" onClick={() => router.push('/home')}>返回主界面</button>
        <span>电量: {state.battery}%</span>
        <span>延迟: {state.latencyMs}ms</span>
        <span>FPS: {state.fps}</span>
        <div className="spacer" />
        <label>
          物件识别
          <input type="checkbox" checked={recognitionEnabled} onChange={(e) => toggleRecognition(e.target.checked)} />
        </label>
      </div>

      <div className="ar-main">
        <VideoPanel
          recognitionEnabled={recognitionEnabled}
          targets={targets}
          selectedId={selectedId}
          onSelect={selectTarget}
          streamUrl={streamUrl}
        />

        <div className="card grid">
          <h3>状态区</h3>
          <div>工作状态: {state.workStatus}</div>
          <div>电量: {state.battery}%</div>
          <div>位姿摘要: x={state.pose.x}, y={state.pose.y}, yaw={state.pose.yaw}</div>
          <div>头部状态: pan={state.head.pan}, tilt={state.head.tilt}</div>
          <div>底盘状态: speed={state.base.speed}</div>
          <div>网络状态: WiFi {state.network?.wifiStrength}% / {state.network?.downloadRate}</div>
        </div>
      </div>

      <div className="ar-bottom">
        <div className="card grid">
          <h3>底盘摇杆</h3>
          <Joystick onChange={sendJoystick} />
          <span className="small">支持拖动、死区、松手归零并发送 base_joystick 消息</span>
        </div>
        <div className="card grid">
          <h3>日志区</h3>
          <div className="log-box">
            {logs.map((log, idx) => (
              <div key={`${log.ts}-${idx}`}>[{new Date(log.ts).toLocaleTimeString()}] {log.level}: {log.message}</div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
