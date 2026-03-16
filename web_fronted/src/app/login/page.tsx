'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getApiBase, getAuthToken } from '@/lib/runtime';

export default function LoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (getAuthToken()) {
      router.replace('/home');
    }
  }, [router]);

  const login = async () => {
    if (!account || !password) {
      setError('账号和密码不能为空');
      return;
    }
    setError('');
    try {
      const resp = await fetch(`${getApiBase()}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account, password }),
      });
      const payload = await resp.json();
      if (!resp.ok || !payload?.token) {
        setError(payload?.detail || '登录失败，请检查账号密码');
        return;
      }
      localStorage.setItem('hrt_user', account);
      localStorage.setItem('hrt_token', payload.token);
      router.push('/home');
    } catch {
      setError('网关不可用，请检查服务是否启动');
    }
  };

  return (
    <main className="container" style={{ maxWidth: 440, margin: '8vh auto' }}>
      <div className="card grid">
        <h1>Human-Robot Teaming</h1>
        <label>Account</label>
        <input value={account} onChange={(e) => setAccount(e.target.value)} />
        <label>Password</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type={showPwd ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn secondary" onClick={() => setShowPwd((v) => !v)}>
            {showPwd ? '隐藏' : '显示'}
          </button>
        </div>
        <div className="error">{error}</div>
        <button className="btn" onClick={login}>LOG IN</button>
      </div>
    </main>
  );
}
