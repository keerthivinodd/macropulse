"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  ChevronDown,
  ChevronUp,
  Clipboard,
  ClipboardCheck,
  RefreshCw,
  Send,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";

import ChatHistorySidebar from "@/components/stream/macropulse/ChatHistorySidebar";
import { useChatHistory } from "@/hooks/macropulse/useChatHistory";
import type { ChatMessage } from "@/hooks/macropulse/useChatHistory";
import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { getAgentMetrics, queryMacroPulseAgent } from "@/services/macropulse";
import type { ConversationTurn } from "@/services/macropulse";
import type {
  AgentMetrics,
  MacroPulseAgentQueryResponse,
} from "@/types/macropulse";

// ─── Types ────────────────────────────────────────────────────────────────────

// ─── Suggested prompts ────────────────────────────────────────────────────────

const SUGGESTED_PROMPTS = [
  { icon: TrendingUp, label: "FX Risk", text: "What's the current FX risk for our USD exposure and recommended hedging action?" },
  { icon: Zap, label: "Repo rate impact", text: "Summarize the repo rate impact on our floating rate loan book and expected EMI change." },
  { icon: Sparkles, label: "Crude oil COGS", text: "How will a $20 spike in Brent crude oil affect our COGS and quarterly margins?" },
  { icon: TrendingUp, label: "WPI inflation", text: "What's the WPI inflation outlook for Q4 and how should we adjust procurement pricing?" },
  { icon: Zap, label: "Fed rate scenario", text: "Run a worst-case scenario: Fed rate hike of +100bps. What's the P&L impact?" },
  { icon: Sparkles, label: "India macro", text: "What's the current regional macro posture for India — RBI stance, FX trend, and commodity signal?" },
  { icon: TrendingUp, label: "Combined Q4 impact", text: "Analyze combined macro impact on Q4 margins across interest rate, FX, and crude oil variables." },
  { icon: Zap, label: "CFO brief", text: "Generate a CFO-ready brief summarizing the top 3 macro risks for this week." },
];

const REGION_MAP: Record<string, "India" | "UAE" | "Saudi Arabia"> = {
  IN: "India",
  UAE: "UAE",
  SA: "Saudi Arabia",
};

// ─── Relative time ────────────────────────────────────────────────────────────

function relativeTime(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 10) return "just now";
  if (diff < 60) return `${diff}s ago`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ago`;
}

// ─── Markdown renderer ────────────────────────────────────────────────────────

function renderInline(text: string): React.ReactNode[] {
  // Handles **bold**, *italic*, `code`
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px] text-slate-700"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

interface TableRow { cells: string[] }

function parseTable(lines: string[]): TableRow[] {
  return lines
    .filter((l) => l.startsWith("|") && !l.match(/^\|[-| ]+\|$/))
    .map((l) => ({
      cells: l
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim()),
    }));
}

function MarkdownRenderer({ text }: { text: string }) {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Horizontal rule
    if (line.trim() === "---") {
      nodes.push(<hr key={i} className="my-3 border-gray-200" />);
      i++;
      continue;
    }

    // Table block
    if (line.startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = parseTable(tableLines);
      if (rows.length > 0) {
        const [header, ...body] = rows;
        nodes.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {header.cells.map((c, ci) => (
                    <th
                      key={ci}
                      className="px-3 py-2 text-left text-xs font-bold uppercase tracking-wider text-gray-500"
                    >
                      {renderInline(c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {body.map((row, ri) => (
                  <tr key={ri} className="hover:bg-gray-50">
                    {row.cells.map((c, ci) => (
                      <td key={ci} className="px-3 py-2 text-gray-700">
                        {renderInline(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // H2
    if (line.startsWith("## ")) {
      nodes.push(
        <h2
          key={i}
          className="mb-2 mt-1 border-b border-gray-200 pb-1 text-base font-bold text-gray-900"
        >
          {renderInline(line.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    // H3
    if (line.startsWith("### ")) {
      nodes.push(
        <h3 key={i} className="mb-1 mt-3 text-[13px] font-bold text-gray-800">
          {renderInline(line.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    // Bullet list (- or •)
    if (line.match(/^[-•]\s/)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^[-•]\s/)) {
        items.push(lines[i].replace(/^[-•]\s/, ""));
        i++;
      }
      nodes.push(
        <ul key={`ul-${i}`} className="my-1.5 space-y-1 pl-4">
          {items.map((item, ii) => (
            <li key={ii} className="flex gap-2 text-sm text-gray-700">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
              <span>{renderInline(item)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Numbered list
    if (line.match(/^\d+\.\s/)) {
      const items: string[] = [];
      let num = 1;
      while (i < lines.length && lines[i].match(/^\d+\.\s/)) {
        items.push(lines[i].replace(/^\d+\.\s/, ""));
        i++;
        num++;
      }
      void num;
      nodes.push(
        <ol key={`ol-${i}`} className="my-1.5 list-none space-y-1 pl-0">
          {items.map((item, ii) => (
            <li key={ii} className="flex gap-2 text-sm text-gray-700">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[11px] font-bold text-blue-700">
                {ii + 1}
              </span>
              <span>{renderInline(item)}</span>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Empty line → spacing
    if (line.trim() === "") {
      nodes.push(<div key={i} className="h-2" />);
      i++;
      continue;
    }

    // Plain paragraph
    nodes.push(
      <p key={i} className="text-sm leading-6 text-gray-700">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{nodes}</div>;
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-gray-100 px-4 py-3">
      <div className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="block h-2 w-2 rounded-full bg-gray-400"
            style={{
              animation: "bounce 1.2s infinite",
              animationDelay: `${i * 0.2}s`,
            }}
          />
        ))}
      </div>
      <span className="text-xs text-gray-400">Analyzing macro signals…</span>
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}

// ─── Confidence badge ─────────────────────────────────────────────────────────

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value);
  const color =
    pct >= 85
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : pct >= 70
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-red-50 text-red-700 border-red-200";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${color}`}
    >
      {pct}% confidence
    </span>
  );
}

function PublishBadge({
  status,
}: {
  status: MacroPulseAgentQueryResponse["publish_status"];
}) {
  const styles: Record<string, string> = {
    publish: "bg-emerald-50 text-emerald-700 border-emerald-200",
    review: "bg-blue-50 text-blue-700 border-blue-200",
    hitl_queue: "bg-amber-50 text-amber-700 border-amber-200",
  };
  const labels: Record<string, string> = {
    publish: "Auto-Published",
    review: "Needs Review",
    hitl_queue: "HITL Queue",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

// ─── Sources panel ────────────────────────────────────────────────────────────

function SourcesPanel({
  sources,
}: {
  sources: MacroPulseAgentQueryResponse["sources"];
}) {
  const [expanded, setExpanded] = useState(false);
  if (!sources?.length) return null;

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-800 transition"
      >
        {expanded ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
        {sources.length} source{sources.length !== 1 ? "s" : ""}
      </button>
      {expanded && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {sources.map((src, i) => (
            <div
              key={i}
              className="group relative flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-[11px] font-medium text-gray-600 hover:border-blue-300 hover:text-blue-700 cursor-default"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  src.category === "official"
                    ? "bg-blue-500"
                    : src.category === "market"
                    ? "bg-emerald-500"
                    : src.category === "news"
                    ? "bg-amber-500"
                    : "bg-purple-500"
                }`}
              />
              [{i + 1}] {src.name}
              <div className="pointer-events-none absolute bottom-full left-0 mb-1 hidden w-56 rounded-lg border border-gray-200 bg-white p-2 shadow-lg group-hover:block z-10">
                <p className="text-[11px] font-semibold text-gray-700">{src.name}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{src.detail}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Streaming text ───────────────────────────────────────────────────────────
// Self-contained: only this component re-renders during streaming.

function StreamingText({
  text,
  speed = 38,
  onDone,
}: {
  text: string;
  speed?: number;
  onDone?: () => void;
}) {
  const tokens = useMemo(() => text.split(" "), [text]);
  const [count, setCount] = useState(0);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    setCount(0);
  }, [text]);

  useEffect(() => {
    if (count >= tokens.length) {
      onDoneRef.current?.();
      return;
    }
    const id = setTimeout(() => setCount((c) => c + 1), speed);
    return () => clearTimeout(id);
  }, [count, tokens.length, speed]);

  const displayed = tokens.slice(0, count).join(" ");
  const streaming = count < tokens.length;

  return (
    <>
      <MarkdownRenderer text={displayed} />
      {streaming && (
        <span
          className="ml-0.5 inline-block h-[14px] w-[2px] translate-y-[2px] bg-gray-500"
          style={{ animation: "cursorBlink 0.7s step-end infinite" }}
        />
      )}
    </>
  );
}

// ─── Agent bubble ─────────────────────────────────────────────────────────────

function AgentBubble({
  response,
  isNew,
  timestamp,
}: {
  response: MacroPulseAgentQueryResponse;
  isNew: boolean;
  timestamp: Date;
}) {
  const [copied, setCopied] = useState(false);
  // If not a new message start as done; otherwise wait for stream to finish
  const [streamDone, setStreamDone] = useState(!isNew);

  const copyText = () => {
    const full = [response.impact, response.recommended_action]
      .filter(Boolean)
      .join("\n\n");
    void navigator.clipboard.writeText(full).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div
      className="flex items-start gap-3 max-w-[90%]"
      style={isNew ? { animation: "mpFadeIn 0.35s ease forwards" } : undefined}
    >
      {/* Avatar */}
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#1a2332] shadow-sm">
        <Bot className="h-4 w-4 text-cyan-300" />
      </div>

      <div className="flex-1 space-y-2">
        <div className="rounded-2xl rounded-tl-sm border border-gray-100 bg-white px-5 py-4 shadow-sm space-y-3">
          {isNew && !streamDone ? (
            <StreamingText
              text={response.impact}
              onDone={() => setStreamDone(true)}
            />
          ) : (
            <MarkdownRenderer text={response.impact} />
          )}

          {/* Reveal the rest only after streaming completes */}
          {streamDone && (
            <>
              {/* Badges */}
              <div className="flex flex-wrap gap-2 pt-1">
                <ConfidenceBadge value={response.confidence} />
                <PublishBadge status={response.publish_status} />
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[11px] font-semibold text-slate-600 capitalize">
                  {response.query_type.replace(/_/g, " ")}
                </span>
              </div>

              {response.recommended_action && (
                <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-1.5">
                    Recommended Action
                  </p>
                  <MarkdownRenderer text={response.recommended_action} />
                </div>
              )}

              {response.regional_context && (
                <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-1.5">
                    Regional Context
                  </p>
                  <p className="text-xs leading-5 text-gray-500">
                    {response.regional_context}
                  </p>
                </div>
              )}

              <SourcesPanel sources={response.sources} />
            </>
          )}
        </div>

        <div className="flex items-center gap-3 px-1">
          <span className="text-[11px] text-gray-400">{relativeTime(timestamp)}</span>
          <button
            onClick={copyText}
            title="Copy response"
            className="flex items-center gap-1 text-[11px] text-gray-400 transition hover:text-gray-700"
          >
            {copied ? (
              <ClipboardCheck className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Clipboard className="h-3.5 w-3.5" />
            )}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function MacroPulseAgentPage() {
  const { tenantId, ready } = useMacroPulseTenant();
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isQuerying, setIsQuerying] = useState(false);
  const [newestIdx, setNewestIdx] = useState<number | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const prevSessionIdRef = useRef<string | null>(null);

  const {
    sessions,
    activeSessionId,
    createSession,
    updateSession,
    deleteSession,
    selectSession,
    setActiveSessionId,
    clearAll,
  } = useChatHistory();

  useEffect(() => {
    getAgentMetrics().then(setMetrics).catch(() => null);
  }, []);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input]);

  useEffect(() => {
    if (activeSessionId === prevSessionIdRef.current) return;
    prevSessionIdRef.current = activeSessionId;

    if (!activeSessionId) {
      setMessages([]);
      setNewestIdx(null);
      return;
    }

    const session = sessions.find((item) => item.id === activeSessionId);
    if (session) {
      setMessages(session.messages);
      setNewestIdx(null);
    }
  }, [activeSessionId, sessions]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isQuerying || !ready) return;
      const userMsg = text.trim();
      setInput("");

      let sessionId = activeSessionId;
      if (!sessionId) {
        sessionId = createSession();
      }

      const nextMessages: ChatMessage[] = [
        ...messages,
        { role: "user", text: userMsg, timestamp: new Date() },
      ];

      setMessages(nextMessages);
      updateSession(sessionId, nextMessages);
      setIsQuerying(true);

      try {
        const region = REGION_MAP.IN;
        const history: ConversationTurn[] = nextMessages
          .filter((message) => message.role === "user" || message.role === "agent")
          .map((message) => ({
            role: message.role as "user" | "agent",
            content:
              message.role === "user"
                ? message.text
                : message.response.impact,
          }));

        const response = await queryMacroPulseAgent(
          userMsg,
          tenantId,
          region,
          history
        );

        const next: ChatMessage[] = [
          ...nextMessages,
          { role: "agent", response, timestamp: new Date() },
        ];
        const trimmed = next.length > 50 ? next.slice(next.length - 50) : next;
        setMessages(trimmed);
        setNewestIdx(trimmed.length - 1);
        updateSession(sessionId, trimmed);
      } catch {
        const next: ChatMessage[] = [
          ...nextMessages,
          {
            role: "error",
            text: "Something went wrong. Please try again.",
            timestamp: new Date(),
          },
        ];
        setMessages(next);
        setNewestIdx(null);
        updateSession(sessionId, next);
      } finally {
        setIsQuerying(false);
      }
    },
    [
      activeSessionId,
      createSession,
      isQuerying,
      messages,
      ready,
      tenantId,
      updateSession,
    ]
  );

  // Regenerate: resend the last user message
  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
  const handleRegenerate = () => {
    if (lastUserMsg && lastUserMsg.role === "user") {
      void sendMessage(lastUserMsg.text);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void sendMessage(input);
    }
  };

  const lastMsgIdx = messages.length - 1;
  const lastMsgIsAgent =
    lastMsgIdx >= 0 && messages[lastMsgIdx].role === "agent";

  return (
    <div className="flex h-[calc(100vh-0px)] overflow-hidden">
      <ChatHistorySidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={selectSession}
        onNew={() => {
          setActiveSessionId(null);
          setMessages([]);
          setNewestIdx(null);
        }}
        onDelete={deleteSession}
        onClearAll={() => {
          clearAll();
          setMessages([]);
          setNewestIdx(null);
        }}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((value) => !value)}
      />

      <div className="flex min-w-0 flex-1 flex-col gap-4 bg-[radial-gradient(circle_at_top,_rgba(157,227,229,0.34),_transparent_34%),linear-gradient(180deg,_#eef8f8_0%,_#f8fcfc_100%)] px-6 py-5">
      <style>{`@keyframes mpFadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}@keyframes cursorBlink{0%,100%{opacity:1}50%{opacity:0}}`}</style>
      {/* ── Header ── */}
      <div className="flex shrink-0 items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1a2332] shadow-md">
          <Bot className="h-5 w-5 text-cyan-300" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900">MacroPulse Agent</h2>
          <p className="text-[11px] text-gray-400">
            AI macroeconomic intelligence · {tenantId}
          </p>
        </div>
        <span className="ml-auto flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-600">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          Online
        </span>
      </div>

      {/* ── Suggested prompts (horizontal scroll) ── */}
      {metrics ? (
        <div className="grid shrink-0 grid-cols-2 gap-2 lg:grid-cols-4">
          {[
            ["Requests", String(metrics.total_requests ?? "--")],
            ["p50", metrics.p50_ms != null ? `${metrics.p50_ms.toFixed(0)}ms` : "--"],
            ["p95", metrics.p95_ms != null ? `${metrics.p95_ms.toFixed(0)}ms` : "--"],
            [
              "Confidence",
              metrics.avg_confidence != null
                ? `${metrics.avg_confidence.toFixed(0)}%`
                : "--",
            ],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl border border-slate-100 bg-white px-3 py-2 shadow-sm"
            >
              <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-400">
                {label}
              </p>
              <p className="text-sm font-black text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      ) : null}

      <div className="shrink-0">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">
          Suggested prompts
        </p>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none" style={{ scrollbarWidth: "none" }}>
          {SUGGESTED_PROMPTS.map((p) => (
            <button
              key={p.label}
              onClick={() => void sendMessage(p.text)}
              disabled={isQuerying}
              className="flex shrink-0 items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-gray-700 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50"
            >
              <p.icon className="h-3.5 w-3.5" />
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chat area ── */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
        {/* Messages */}
        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-3 py-20 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#1a2332]/8">
                <Bot className="h-8 w-8 text-[#1a2332]/30" />
              </div>
              <p className="text-sm font-semibold text-gray-400">
                Ask MacroPulse anything about macro, FX, rates, or commodities
              </p>
              <p className="text-xs text-gray-300">
                or pick a suggested prompt above
              </p>
            </div>
          )}

          {/* Message list */}
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "agent" ? (
                <AgentBubble
                  response={m.response}
                  isNew={newestIdx === i}
                  timestamp={m.timestamp}
                />
              ) : m.role === "error" ? (
                <div className="max-w-[75%] rounded-2xl rounded-tl-sm border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {m.text}
                </div>
              ) : (
                <div className="max-w-[70%] space-y-1">
                  <div className="rounded-2xl rounded-tr-sm bg-[#1a2332] px-4 py-3 text-sm leading-6 text-white">
                    {m.text}
                  </div>
                  <p className="px-1 text-right text-[11px] text-gray-400">
                    {relativeTime(m.timestamp)}
                  </p>
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isQuerying && (
            <div className="flex justify-start">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#1a2332] shadow-sm">
                  <Bot className="h-4 w-4 text-cyan-300" />
                </div>
                <TypingIndicator />
              </div>
            </div>
          )}

          {/* Regenerate button */}
          {lastMsgIsAgent && !isQuerying && (
            <div className="flex justify-start pl-11">
              <button
                onClick={handleRegenerate}
                className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-500 transition hover:border-gray-300 hover:text-gray-700"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Regenerate
              </button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Input area ── */}
        <div className="shrink-0 border-t border-gray-100 p-4">
          <div className="flex items-end gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 focus-within:border-blue-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-blue-100 transition">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="Ask about macro conditions, FX risk, rates, or run a scenario…"
              className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
              style={{ maxHeight: "120px" }}
            />
            <div className="flex shrink-0 flex-col items-end gap-1">
              {input.length > 200 && (
                <span
                  className={`text-[10px] font-medium ${
                    input.length > 800 ? "text-red-500" : "text-gray-400"
                  }`}
                >
                  {input.length}/1000
                </span>
              )}
              <button
                onClick={() => void sendMessage(input)}
                disabled={isQuerying || !input.trim()}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#1a2332] transition hover:bg-[#243044] disabled:opacity-40"
              >
                <Send className="h-4 w-4 text-white" />
              </button>
            </div>
          </div>
          <p className="mt-2 text-center text-[10px] text-gray-300">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
    </div>
  );
}

