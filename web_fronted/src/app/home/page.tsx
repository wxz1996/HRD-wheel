'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authHeaders, getApiBase, getAuthToken } from '@/lib/runtime';

type Summary = {
  robotId: string;
  robotName: string;
  workStatus: string;
  battery: number;
  statusSummary: { pose: string; head: string; base: string };
  logs: { ts: string; level: string; message: string }[];
};

export default function HomePage() {
  const router = useRouter();
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.replace('/login');
      return;
    }
    fetch(`${getApiBase()}/api/robot/summary`, { headers: authHeaders(token) })
      .then(async (r) => {
        if (r.status === 401) {
          localStorage.removeItem('hrt_token');
          router.replace('/login');
          return null;
        }
        return r.json();
      })
      .then((payload) => payload && setSummary(payload))
      .catch(() => undefined);
  }, [router]);

  return (
    <main className="container grid">
      <h1>HRT 控制台 / Home</h1>
      <div className="grid home-grid">
        <div className="card grid">
          <h3>机器人摘要</h3>
          <div>机器人编号：{summary?.robotId ?? 'robot-001'}</div>
          <div>工作状态：{summary?.workStatus ?? '待机中'}</div>
          <div>电量：{summary?.battery ?? 78}%</div>
          <div>状态摘要：{summary?.statusSummary.pose ?? 'x=1.2,y=0.5,yaw=0.3'}</div>
          <div>日志预览：{summary?.logs?.[0]?.message ?? '等待事件...'}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" onClick={() => router.push('/ar')}>进入 AR 控制</button>
            <button
              className="btn secondary"
              onClick={() => {
                localStorage.removeItem('hrt_token');
                localStorage.removeItem('hrt_user');
                router.push('/login');
              }}
            >
              退出登录
            </button>
          </div>
        </div>
        <div className="card grid">
          <h3>占位模块</h3>
          <div>导航系统模块（占位）</div>
          <div>任务队列（占位）</div>
          <div>设置 / 支持 / 我的（占位）</div>
          <div>任务执行模块（占位）</div>
        </div>
      </div>
    </main>
  );
}
