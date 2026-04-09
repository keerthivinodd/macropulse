"use client";

import { useCallback, useEffect, useState } from "react";

import type { MacroPulseAgentQueryResponse } from "@/types/macropulse";

export type ChatMessage =
  | { role: "user"; text: string; timestamp: Date }
  | {
      role: "agent";
      response: MacroPulseAgentQueryResponse;
      timestamp: Date;
    }
  | { role: "error"; text: string; timestamp: Date };

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "macropulse_chat_history";
const MAX_SESSIONS = 50;

function generateId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function serializeSessions(sessions: ChatSession[]): string {
  return JSON.stringify(
    sessions.slice(0, MAX_SESSIONS).map((session) => ({
      ...session,
      messages: session.messages.map((message) => ({
        ...message,
        timestamp: message.timestamp.toISOString(),
      })),
    }))
  );
}

function deserializeSessions(raw: string | null): ChatSession[] {
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as Array<
      Omit<ChatSession, "messages"> & {
        messages: Array<Omit<ChatMessage, "timestamp"> & { timestamp: string }>;
      }
    >;

    return parsed.map((session) => ({
      ...session,
      messages: session.messages.map((message) => ({
        ...message,
        timestamp: new Date(message.timestamp),
      })) as ChatMessage[],
    }));
  } catch {
    return [];
  }
}

function deriveTitle(messages: ChatMessage[]): string {
  const firstUserMessage = messages.find((message) => message.role === "user");

  if (!firstUserMessage || firstUserMessage.role !== "user") {
    return "New chat";
  }

  const title = firstUserMessage.text.trim();
  return title.length > 56 ? `${title.slice(0, 53)}...` : title;
}

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const loadedSessions = deserializeSessions(
      window.localStorage.getItem(STORAGE_KEY)
    );
    setSessions(loadedSessions);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    if (sessions.length === 0) {
      window.localStorage.removeItem(STORAGE_KEY);
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, serializeSessions(sessions));
  }, [sessions]);

  const activeSession =
    sessions.find((session) => session.id === activeSessionId) ?? null;

  const createSession = useCallback((): string => {
    const sessionId = generateId();
    const now = Date.now();
    const nextSession: ChatSession = {
      id: sessionId,
      title: "New chat",
      messages: [],
      createdAt: now,
      updatedAt: now,
    };

    setSessions((prev) => [nextSession, ...prev].slice(0, MAX_SESSIONS));
    setActiveSessionId(sessionId);
    return sessionId;
  }, []);

  const updateSession = useCallback((id: string, messages: ChatMessage[]) => {
    setSessions((prev) => {
      const now = Date.now();
      const nextSessions = prev.map((session) =>
        session.id === id
          ? {
              ...session,
              messages,
              title: deriveTitle(messages),
              updatedAt: now,
            }
          : session
      );

      nextSessions.sort((a, b) => b.updatedAt - a.updatedAt);
      return nextSessions;
    });
  }, []);

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => prev.filter((session) => session.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
      }
    },
    [activeSessionId]
  );

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const clearAll = useCallback(() => {
    setSessions([]);
    setActiveSessionId(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  return {
    sessions,
    activeSession,
    activeSessionId,
    createSession,
    updateSession,
    deleteSession,
    selectSession,
    setActiveSessionId,
    clearAll,
  };
}
