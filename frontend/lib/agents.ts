export type AgentId =
  | "main"
  | "recruiting"
  | "transfer-portal"
  | "scenario"
  | "hidden-gem"
  | "roster-builder"
  | "scouting"
  | "player-development"
  | "compare"
  | "risk-fit"
  | "market-inefficiency"
  | "game-plan";

export type Agent = {
  id: AgentId;
  name: string;
  emoji: string;
  tagline: string;
  problemSolved: string;
  description: string;
  chips: string[];
  route: string | null;
};

export const AGENTS: Agent[] = [
  {
    id: "main",
    name: "Front Office AI",
    emoji: "🏀",
    tagline: "Your central basketball operations assistant",
    problemSolved: "Staff no longer need to jump between disconnected tools to make roster decisions.",
    description: "Detects intent from your message and routes to the right specialist agent — recruiting, scouting, roster, transfer, or player comparisons.",
    chips: [
      "What should Illinois do in the transfer portal?",
      "Find a 3-and-D wing for Illinois",
      "Who are the hidden gems on the board?",
      "What are Illinois's biggest roster needs?",
      "Compare the top two portal targets",
    ],
    route: null,
  },
  {
    id: "recruiting",
    name: "Recruiting Agent",
    emoji: "🎯",
    tagline: "Ranked, explainable recruiting boards",
    problemSolved: "Coaches need a prioritized, evidence-backed board instead of raw stats sheets.",
    description: "Generates GM Priority Boards, Illinois Fit tiers, role-based shortlists, safe-floor targets, swing bets, and overvalued-risk flags — all tuned to Brad Underwood's system.",
    chips: [
      "Show me the Illinois recruiting board",
      "Find 3-and-D wings for Underwood's system",
      "Who are Tier 1 targets this cycle?",
      "Who fits Illinois's offensive identity?",
      "Show low-risk, high-fit targets only",
    ],
    route: "/recruiting-center",
  },
  {
    id: "transfer-portal",
    name: "Transfer Portal Agent",
    emoji: "🔄",
    tagline: "Data-ranked portal decisions",
    problemSolved: "Portal decisions move fast and a bad add can hurt the program for 2–3 years.",
    description: "Ranks portal targets using our scoring system. Shows predicted BPM, success probability, conference translation, and risk.",
    chips: [
      "Who are the top-ranked portal targets?",
      "Show high-ceiling low-risk transfers",
      "Who has the best conference translation to Big Ten?",
      "Find guards with strong success scores",
      "Show me the full portal rankings",
    ],
    route: "/transfer-success-predictor",
  },
  {
    id: "scenario",
    name: "Scenario Agent",
    emoji: "♟️",
    tagline: "Simulate roster moves before committing",
    problemSolved: "GMs need to understand tradeoffs and team identity shifts before offering scholarships.",
    description: "Interactive add/remove roster simulations. Tracks scholarship count, depth chart impact, shooting/rebounding/defense changes, and recommends best moves.",
    chips: [
      "What happens if we add a stretch big?",
      "Simulate replacing our starting guard",
      "How many scholarships do we have?",
      "What does our depth chart look like?",
      "Show me our positional gaps",
    ],
    route: "/roster-builder",
  },
  {
    id: "hidden-gem",
    name: "Hidden Gem Agent",
    emoji: "💎",
    tagline: "Find players before the market does",
    problemSolved: "Illinois can gain a real edge by identifying undervalued players before public consensus catches up.",
    description: "Surfaces Hidden Gem Score, Market Inefficiency Score, low-visibility/high-production flags, small-school translation adjustments, and explains why others may miss a player.",
    chips: [
      "Identify hidden gem recruits",
      "Find undervalued players in the portal",
      "Who is overranked by public scouts?",
      "Show small-school hidden gems",
      "Who has high production and low attention?",
    ],
    route: "/hidden-gem-lab",
  },
  {
    id: "roster-builder",
    name: "Roster Builder Agent",
    emoji: "🏗️",
    tagline: "Build a complete Illinois roster plan",
    problemSolved: "Staff need to balance talent, roles, scholarships, and future recruiting classes simultaneously.",
    description: "View current roster, build depth charts, allocate scholarships, project rotations, identify role gaps, summarize team weaknesses, and recommend target types.",
    chips: [
      "Build a 2026 roster plan",
      "Show me our current depth chart",
      "Where are our biggest roster gaps?",
      "How balanced is our rotation?",
      "What type of player do we need most?",
    ],
    route: "/roster-builder",
  },
  {
    id: "scouting",
    name: "Scouting Agent",
    emoji: "📋",
    tagline: "Instant scouting reports and opponent prep",
    problemSolved: "Coaches need fast, actionable scouting reports they can use before games and recruiting calls.",
    description: "Generates player scouting reports with strengths, weaknesses, shot profile, defensive tendencies, key matchups, game plan recommendations, and PDF export.",
    chips: [
      "Generate a scouting report for the top target",
      "What are this player's weaknesses at Illinois?",
      "How does this player fit Underwood's defense?",
      "Scout the best available shooting guard",
      "Show strengths and concerns for top portal guard",
    ],
    route: "/scouting-center",
  },
  {
    id: "player-development",
    name: "Player Development Agent",
    emoji: "📈",
    tagline: "Data-backed individual development plans",
    problemSolved: "Development priorities should be grounded in data, not just intuition.",
    description: "Identifies player strengths and weaknesses, improvement priorities, skill development paths, comparable player trajectories, and role expansion opportunities.",
    chips: [
      "Who has the highest projected BPM ceiling?",
      "Which portal target has the most development upside?",
      "What should our top target work on at Illinois?",
      "Find players who can expand their role in Underwood's system",
      "Show development paths for wing players",
    ],
    route: "/player-intelligence",
  },
  {
    id: "compare",
    name: "Compare Players Agent",
    emoji: "⚖️",
    tagline: "Side-by-side player decisions",
    problemSolved: "Coaches often choose between similar portal targets and need structured comparison, not gut feel.",
    description: "Side-by-side stats, fit/risk/upside comparison, radar chart, similarity score, and clear recommendation for safer pick, higher upside, or best Illinois fit.",
    chips: [
      "Compare two portal forwards",
      "Who is the better Illinois fit?",
      "Show radar chart comparison",
      "Which player is lower risk?",
      "Who has more upside?",
    ],
    route: "/compare-players",
  },
  {
    id: "risk-fit",
    name: "Risk & Fit Agent",
    emoji: "🛡️",
    tagline: "Clear, explainable risk assessment",
    problemSolved: "Raw rankings miss fit, role mismatches, and efficiency red flags that matter in college basketball.",
    description: "Breaks down Risk Score, Illinois Fit Score, red flags, role mismatch warnings, and confidence levels with full explainable reasoning for each decision.",
    chips: [
      "Show low-risk, high-fit targets for Illinois",
      "Flag role mismatches in Underwood's system",
      "Who are the safest floor additions this cycle?",
      "Which targets have red flags we should know about?",
      "Show the risk vs fit matrix for top targets",
    ],
    route: "/player-intelligence",
  },
  {
    id: "market-inefficiency",
    name: "Market Inefficiency Agent",
    emoji: "📊",
    tagline: "Find value before the market prices it in",
    problemSolved: "Programs with limited resources need smarter filters to find value others miss.",
    description: "Identifies undervalued target boards, high-production/low-visibility players, low-usage/high-efficiency standouts, and strong role fits with low public rankings.",
    chips: [
      "Show most undervalued portal players",
      "Find high production, low attention targets",
      "Who is the market sleeping on?",
      "Show low-usage, high-efficiency players",
      "Find value in mid-major programs",
    ],
    route: "/hidden-gem-lab",
  },
  {
    id: "game-plan",
    name: "Game Plan Agent",
    emoji: "🎮",
    tagline: "Fast, usable opponent and matchup prep",
    problemSolved: "Staff need quick, structured prep before games — player threats, defensive schemes, and offensive attack points.",
    description: "Generates opponent strengths and weaknesses, player-by-player threat levels, defensive game plans, offensive attack points, and matchup recommendations.",
    chips: [
      "Create an opponent scouting report",
      "Who is their biggest offensive threat?",
      "How should we defend their pick-and-roll?",
      "Show matchup recommendations",
      "What are their defensive weaknesses?",
    ],
    route: "/scouting-center",
  },
];

export function getAgent(id: AgentId): Agent {
  return AGENTS.find((a) => a.id === id) ?? AGENTS[0];
}
