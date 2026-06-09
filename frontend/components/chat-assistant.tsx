"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, RotateCcw, User, Bot } from "lucide-react";

import { NavigationAction, apiPost } from "@/lib/api";
import { getAgent, type AgentId } from "@/lib/agents";

type Message = {
  role: "user" | "assistant";
  content: string;
  navigation?: NavigationAction[];
  loading?: boolean;
};

type ChatResponse = {
  answer: string;
  evidence: Array<Record<string, unknown>>;
  navigation: NavigationAction[];
  routed_agent_id?: string | null;
};

type Props = {
  activeAgent?: AgentId;
  onAgentChange?: (id: AgentId) => void;
};

export function ChatAssistant({ activeAgent = "main", onAgentChange }: Props): JSX.Element {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const agent = getAgent(activeAgent);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Reset conversation when agent changes
  useEffect(() => {
    setMessages([]);
    setInput("");
  }, [activeAgent]);

  async function send(query: string): Promise<void> {
    if (!query.trim()) return;
    const userMsg: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await apiPost<ChatResponse>("/chat", {
        message: query,
        agent_id: activeAgent,
      });

      // If the backend routed to a specialist agent, switch the active agent in the UI
      if (res.routed_agent_id && onAgentChange) {
        onAgentChange(res.routed_agent_id as AgentId);
      }

      const assistantMsg: Message = {
        role: "assistant",
        content: res.answer,
        navigation: res.navigation ?? [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Unable to reach the analytics backend. Make sure the server is running on localhost:8000.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleChip(chip: string) {
    void send(chip);
  }

  function clearChat() {
    setMessages([]);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* ── Conversation thread ───────────────────────────────────────── */}
      {hasMessages && (
        <div className="flex max-h-[480px] flex-col gap-3 overflow-y-auto rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              {/* Avatar */}
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs ${
                  msg.role === "user"
                    ? "bg-orange text-white"
                    : "bg-navy/80 text-white/80"
                }`}
              >
                {msg.role === "user" ? (
                  <User size={13} />
                ) : (
                  <span className="text-[10px]">{agent.emoji}</span>
                )}
              </div>

              {/* Bubble */}
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                  msg.role === "user"
                    ? "rounded-tr-sm bg-orange/80 text-white"
                    : "rounded-tl-sm bg-white/10 text-white"
                }`}
              >
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>

                {/* Navigation chips */}
                {msg.navigation && msg.navigation.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {msg.navigation.map((nav) => (
                      <Link
                        key={nav.path}
                        href={nav.path}
                        className="rounded-full border border-orange/50 bg-orange/20 px-2.5 py-1 text-[11px] font-medium text-white/90 transition hover:bg-orange/35"
                        title={nav.reason}
                      >
                        {nav.label} →
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy/80 text-[10px]">
                {agent.emoji}
              </div>
              <div className="rounded-2xl rounded-tl-sm bg-white/10 px-4 py-3">
                <Loader2 size={15} className="animate-spin text-white/50" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}

      {/* ── Input row ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 rounded-2xl border border-white/30 bg-white/95 p-2 shadow-panel backdrop-blur-sm">
        <input
          ref={inputRef}
          className="h-12 flex-1 rounded-xl border border-slate-200 bg-white px-4 text-[15px] text-slate-800 outline-none transition focus:border-orange focus:ring-2 focus:ring-orange/25"
          placeholder={`Ask ${agent.name}…`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) void send(input);
          }}
          disabled={loading}
        />

        {hasMessages && (
          <button
            onClick={clearChat}
            className="flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 text-slate-400 transition hover:border-slate-300 hover:text-slate-600"
            title="Clear conversation"
          >
            <RotateCcw size={16} />
          </button>
        )}

        <button
          className="flex h-12 w-12 items-center justify-center rounded-xl bg-orange text-white transition hover:bg-navy disabled:opacity-50"
          onClick={() => void send(input)}
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          {loading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <ArrowUp size={18} />
          )}
        </button>
      </div>

      {/* ── Prompt chips (shown when no conversation yet) ─────────────── */}
      {!hasMessages && !loading && (
        <div className="flex flex-wrap justify-center gap-2">
          {agent.chips.map((chip) => (
            <button
              key={chip}
              onClick={() => handleChip(chip)}
              className="rounded-full border border-white/25 bg-white/10 px-3 py-1.5 text-xs text-white/80 transition hover:bg-white/20 hover:text-white"
            >
              {chip}
            </button>
          ))}
        </div>
      )}

      {/* ── Post-reply chip suggestions ───────────────────────────────── */}
      {hasMessages && !loading && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {agent.chips.slice(0, 3).map((chip) => (
            <button
              key={chip}
              onClick={() => handleChip(chip)}
              className="rounded-full border border-white/15 bg-white/8 px-3 py-1 text-[11px] text-white/50 transition hover:bg-white/15 hover:text-white/80"
            >
              {chip}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
