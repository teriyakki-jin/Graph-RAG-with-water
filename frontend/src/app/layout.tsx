import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Graph RAG — 수처리 지식 그래프",
  description: "수처리 도메인 지식 그래프 기반 RAG 시스템",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="antialiased">{children}</body>
    </html>
  );
}
