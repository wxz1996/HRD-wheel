'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');

  const login = async () => {
    if (!account || !password) {
      setError('账号和密码不能为空');
      return;
    }
    setError('');
    await fetch('http://localhost:8000/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ account, password }),
    });
    localStorage.setItem('hrt_user', account);
    router.push('/home');
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
