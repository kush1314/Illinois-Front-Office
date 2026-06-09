"use client";

import { useEffect, useState } from "react";
import { ChatAssistant } from "@/components/chat-assistant";
import { apiGet } from "@/lib/api";
import type { AgentId } from "@/lib/agents";
import { AGENTS } from "@/lib/agents";

type HealthData = {
  status: string;
  ml_trained: string;
  training_rows: string;
  model_stack: string;
};

// All 12 agents displayed — exclude "main" (it is the default state, not a specialist)
const AGENT_QUICK = AGENTS.filter((a) => a.id !== "main");

export default function HomePage(): JSX.Element {
  const [activeAgent, setActiveAgent] = useState<AgentId>("main");
  useEffect(() => {
    // ping backend to warm up the connection
    apiGet<HealthData>("/health").catch(() => {});
  }, []);

  const activeAgentObj = AGENTS.find((a) => a.id === activeAgent) ?? AGENTS[0];

  return (
    <div className="landing-bg flex min-h-screen flex-col">


      {/* Main */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-6 md:px-8">
        <div className="w-full max-w-2xl">
          {/* Hero */}
          <div className="mb-7 text-center">
            <h1 className="text-4xl font-extrabold leading-[1.1] tracking-tight text-white md:text-5xl lg:text-[52px]">
              Illinois Front<br />
              <span className="text-orange">Office AI</span>
            </h1>
            <p className="mt-3 text-sm text-white/60 md:text-base">
              {activeAgent === "main"
                ? "Ask any basketball question relating to Illinois."
                : `${activeAgentObj.name}: ${activeAgentObj.tagline}`}
            </p>
          </div>

          {/* Chat interface */}
          <ChatAssistant activeAgent={activeAgent} onAgentChange={setActiveAgent} />

          {/* All 11 specialist agents */}
          <div className="mt-5">
            <p className="mb-2 text-center text-[10px] font-semibold uppercase tracking-widest text-white/30">
              Switch specialist agent
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              {AGENT_QUICK.map((a) => (
                <button
                  key={a.id}
                  onClick={() => setActiveAgent(a.id)}
                  className={`rounded-full border px-3 py-1.5 text-[11px] font-medium transition ${
                    activeAgent === a.id
                      ? "border-orange bg-orange/20 text-white"
                      : "border-white/12 bg-white/5 text-white/55 hover:border-white/25 hover:text-white/85"
                  }`}
                >
                  {a.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="pb-4 text-center text-[10px] text-white/20">
        PortalGPT · Illinois Men's Basketball
      </footer>
    </div>
  );
}
