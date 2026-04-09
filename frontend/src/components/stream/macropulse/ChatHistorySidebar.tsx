"use client";

import { useState } from "react";
import {
  Clock,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Trash2,
} from "lucide-react";

import type { ChatSession } from "@/hooks/macropulse/useChatHistory";

function formatTimeAgo(timestamp: number): string {
  const diffMs = Date.now() - timestamp;
  const minutes = Math.floor(diffMs / 60000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days}d ago`;

  return new Date(timestamp).toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
  });
}

function groupSessions(sessions: ChatSession[]) {
  const now = Date.now();
  const groups = {
    Today: [] as ChatSession[],
    Yesterday: [] as ChatSession[],
    "This week": [] as ChatSession[],
    Older: [] as ChatSession[],
  };

  sessions.forEach((session) => {
    const days = (now - session.updatedAt) / 86400000;
    if (days < 1) groups.Today.push(session);
    else if (days < 2) groups.Yesterday.push(session);
    else if (days < 7) groups["This week"].push(session);
    else groups.Older.push(session);
  });

  return Object.entries(groups)
    .map(([label, items]) => ({ label, items }))
    .filter((group) => group.items.length > 0);
}

interface ChatHistorySidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
  collapsed: boolean;
  onToggle: () => void;
}

export default function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
  onClearAll,
  collapsed,
  onToggle,
}: ChatHistorySidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const groupedSessions = groupSessions(sessions);

  if (collapsed) {
    return (
      <aside className="flex w-12 shrink-0 flex-col items-center gap-3 border-r border-slate-200 bg-slate-50 py-3">
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-200"
          title="Open chat history"
        >
          <PanelLeftOpen className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={onNew}
          className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-200"
          title="New chat"
        >
          <Plus className="h-4 w-4" />
        </button>
      </aside>
    );
  }

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-slate-200 bg-slate-50">
      <div className="flex items-center justify-between px-4 pb-2 pt-4">
        <span className="text-xs font-bold uppercase tracking-[0.25em] text-slate-400">
          Chat History
        </span>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-200"
          title="Close sidebar"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      <div className="px-4 pb-3">
        <button
          type="button"
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-100"
        >
          <Plus className="h-4 w-4" />
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {sessions.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center text-slate-400">
            <MessageSquare className="mb-2 h-8 w-8 opacity-40" />
            <p className="text-xs">No conversations yet</p>
          </div>
        ) : (
          groupedSessions.map((group) => (
            <div key={group.label} className="mt-3 first:mt-0">
              <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                {group.label}
              </p>
              {group.items.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => onSelect(session.id)}
                  onMouseEnter={() => setHoveredId(session.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-left transition ${
                    activeSessionId === session.id
                      ? "border border-blue-200 bg-blue-50 text-blue-900"
                      : "border border-transparent text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  <MessageSquare
                    className={`h-3.5 w-3.5 shrink-0 ${
                      activeSessionId === session.id
                        ? "text-blue-500"
                        : "text-slate-400"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">
                      {session.title}
                    </p>
                    <p className="mt-0.5 flex items-center gap-1 text-[10px] text-slate-400">
                      <Clock className="h-2.5 w-2.5" />
                      {formatTimeAgo(session.updatedAt)}
                      <span className="ml-auto">
                        {
                          session.messages.filter(
                            (message) => message.role === "user"
                          ).length
                        }{" "}
                        msgs
                      </span>
                    </p>
                  </div>
                  {hoveredId === session.id ? (
                    <span
                      role="button"
                      tabIndex={0}
                      onClick={(event) => {
                        event.stopPropagation();
                        onDelete(session.id);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          event.stopPropagation();
                          onDelete(session.id);
                        }
                      }}
                      className="rounded-md p-1 text-slate-400 transition hover:bg-red-100 hover:text-red-500"
                      title="Delete conversation"
                    >
                      <Trash2 className="h-3 w-3" />
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          ))
        )}
      </div>

      {sessions.length > 0 ? (
        <div className="border-t border-slate-200 px-4 py-3">
          {confirmClear ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-red-600">Delete all?</span>
              <button
                type="button"
                onClick={() => {
                  onClearAll();
                  setConfirmClear(false);
                }}
                className="rounded bg-red-500 px-2 py-1 text-[11px] font-medium text-white hover:bg-red-600"
              >
                Yes
              </button>
              <button
                type="button"
                onClick={() => setConfirmClear(false)}
                className="rounded bg-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-300"
              >
                No
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmClear(true)}
              className="flex items-center gap-1.5 text-[11px] text-slate-400 transition hover:text-red-500"
            >
              <Trash2 className="h-3 w-3" />
              Clear all conversations
            </button>
          )}
        </div>
      ) : null}
    </aside>
  );
}
