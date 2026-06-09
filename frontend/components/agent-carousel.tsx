"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, X, Zap } from "lucide-react";
import Link from "next/link";
import { AGENTS, type Agent, type AgentId } from "@/lib/agents";

type Props = {
  activeAgent: AgentId;
  onAgentChange: (id: AgentId) => void;
};

export function AgentCarousel({ activeAgent, onAgentChange }: Props): JSX.Element {
  const [open, setOpen] = useState(false);
  const currentIndex = AGENTS.findIndex((a) => a.id === activeAgent);
  const current = AGENTS[currentIndex];

  function prev() {
    const next = (currentIndex - 1 + AGENTS.length) % AGENTS.length;
    onAgentChange(AGENTS[next].id);
  }

  function next() {
    const n = (currentIndex + 1) % AGENTS.length;
    onAgentChange(AGENTS[n].id);
  }

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-sm text-white/90 transition hover:bg-white/20"
      >
        <span className="text-base leading-none">{current.emoji}</span>
        <span className="max-w-[130px] truncate font-medium">{current.name}</span>
        <Zap className="h-3.5 w-3.5 text-orange" />
      </button>

      {/* Popover panel */}
      {open && (
        <div className="absolute right-0 top-10 z-50 w-[340px] rounded-2xl border border-white/10 bg-[#0e1f3d]/95 shadow-2xl backdrop-blur-md">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-widest text-orange">Switch Agent</p>
            <button onClick={() => setOpen(false)} className="text-white/50 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Carousel */}
          <div className="p-4">
            <div className="flex items-center gap-3">
              <button
                onClick={prev}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 text-white/70 transition hover:border-orange/60 hover:text-orange"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              <div className="flex-1 text-center">
                <div className="text-3xl leading-none">{current.emoji}</div>
                <div className="mt-1.5 text-base font-bold text-white">{current.name}</div>
                <div className="mt-0.5 text-xs text-white/60">{current.tagline}</div>
                <div className="mt-1 text-xs font-medium text-orange/80">
                  {currentIndex + 1} / {AGENTS.length}
                </div>
              </div>

              <button
                onClick={next}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-white/15 text-white/70 transition hover:border-orange/60 hover:text-orange"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <p className="mt-3 text-center text-xs text-white/55">{current.description}</p>

            <div className="mt-3 flex gap-2">
              <button
                onClick={() => {
                  onAgentChange(current.id);
                  setOpen(false);
                }}
                className="flex-1 rounded-lg bg-orange py-2 text-xs font-semibold text-white transition hover:bg-orange/90"
              >
                Use this agent
              </button>
              {current.route && (
                <Link
                  href={current.route}
                  onClick={() => setOpen(false)}
                  className="flex-1 rounded-lg border border-white/20 py-2 text-center text-xs font-semibold text-white/80 transition hover:bg-white/10"
                >
                  Open dashboard →
                </Link>
              )}
            </div>
          </div>

          {/* All agents grid */}
          <div className="border-t border-white/10 px-4 pb-4 pt-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-white/40">All Agents</p>
            <div className="grid grid-cols-3 gap-1.5">
              {AGENTS.map((agent: Agent) => (
                <button
                  key={agent.id}
                  onClick={() => {
                    onAgentChange(agent.id);
                    setOpen(false);
                  }}
                  className={`flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 text-center transition ${
                    agent.id === activeAgent
                      ? "bg-orange/20 ring-1 ring-orange/50"
                      : "hover:bg-white/10"
                  }`}
                >
                    <span className="text-xl leading-none">{agent.emoji}</span>
                    <span className="mt-0.5 text-[10px] font-medium leading-tight text-white/80">{agent.name}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
