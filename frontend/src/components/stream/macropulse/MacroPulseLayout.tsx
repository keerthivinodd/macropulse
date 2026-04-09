"use client";

import MacroPulseSidebar from "./MacroPulseSidebar";

export default function MacroPulseLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="flex min-h-screen overflow-hidden macropulse-shell text-slate-900"
      style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
    >
      <MacroPulseSidebar />
      <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
