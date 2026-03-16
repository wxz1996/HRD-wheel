import './globals.css';
import { ReactNode } from 'react';

export const metadata = {
  title: 'HRT MVP',
  description: 'Human-Robot Teaming MVP Demo',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
