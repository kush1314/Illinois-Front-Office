# Illinois Front Office

A web platform for evaluating transfer portal targets, built for the Illinois Men's Basketball Analytics Internship.

---

## The Problem

When a player enters the transfer portal, a coaching staff might have 48 hours to decide whether to pursue him. To make that decision they need his stats, an understanding of how his game fits the system, a risk assessment, comparable players, and a sense of what he'd do to the current roster. That information sits across BartTorvik, Sports Reference, internal spreadsheets, and film notes with nothing connecting them. By the time you pull it all together manually, he may already be committed somewhere else.

The bottleneck is not lack of data. It's turning scattered information into a decision fast enough to act on it.

---

## The Solution

Illinois Front Office is a single workflow for answering one question: should we pursue this player?

You type a question in plain English and the platform routes it to the right mode automatically. There are 12 specialized modes, each covering a different part of the evaluation. The chat is powered by Google Gemini when you have an API key. Without one, everything still works through the rule-based logic built into each mode.

### The 12 Modes

**Front Office (main):** The starting point. Reads your question, figures out what you're asking, and routes to the right specialist automatically. Ask anything and it handles it or hands it off.

**Recruiting Agent:** Builds a tiered recruiting board for Illinois tuned to Brad Underwood's system. Outputs a Tier 1 contact list, role-based shortlists for wings, guards, and bigs, safe floor targets, swing bets with upside, and players to avoid. Not a sorted spreadsheet — a board organized around what Illinois actually needs.

**Transfer Portal Agent:** Takes the full player pool and ranks everyone by predicted transfer success. Pulls from the prediction model to surface who is most likely to contribute at a Big Ten level, with success probability, projected BPM, and conference translation score for each player.

**Risk and Fit Agent:** Scores every player on two things independently — how well they fit Underwood's system, and how much risk they carry. Fit looks at three-point shooting, defensive rating, assist rate, and usage efficiency against Illinois's specific thresholds. Risk flags things like small sample size, high turnover rate, poor free-throw shooting, and conference mismatch. Gives you a clean answer on who is safe to pursue and who needs more diligence.

**Hidden Gem Agent:** Finds players the market is undervaluing. Compares the prediction model's ranking of a player against their public attention level. When the model thinks a player is significantly better than their public ranking suggests, that gap is the competitive advantage — a player Illinois can move on before other programs recognize the same thing.

**Market Inefficiency Agent:** Similar to the Hidden Gem Agent but focused on production relative to attention. Surfaces players with strong efficiency numbers who are flying under the radar, particularly from mid-major programs where visibility is lower.

**Compare Players Agent:** Side-by-side evaluation of two players across stats, fit scores, risk, and projected impact. Includes a radar chart and outputs a clear recommendation: which is the safer floor, which has the higher ceiling, and which is the better Illinois fit.

**Roster Builder Agent:** Shows the current Illinois roster, maps out the depth chart, and identifies positional gaps. Tells you what type of player the program needs most based on what's already there.

**Scenario Agent:** Simulates roster moves before committing to them. Add a hypothetical player and see how the depth chart, shooting balance, defensive profile, and positional distribution change. Helps answer "what happens if we add a stretch big?" before a scholarship offer goes out.

**Scouting Agent:** Generates a full scouting report for any player in the dataset — strengths, concerns, shot profile, Illinois fit verdict, and key development questions. Exportable as a PDF ready to send to the full coaching staff.

**Player Development Agent:** For players already on the board or on the roster, shows ceiling projections, skill development priorities, comparable player trajectories, and role expansion opportunities grounded in the statistical profile.

**Game Plan Agent:** Opponent prep. Given a player or team, surfaces the primary offensive and defensive threats, suggested defensive schemes, matchup recommendations, and attacking points for the offensive end.

---

## The Prediction Model

The model's job is to predict what happens to a player's production when they transfer. It looks at 16 stats per player including shooting efficiency (TS%), usage rate, assist rate, turnover rate, rebounding, defensive rating, prior BPM, and — critically — how large a conference jump they're making. It then outputs two things:

**1. Transfer success probability (0-100):** how likely is this transfer to work out, defined as landing at a positive BPM at the new school.

**2. Projected BPM at Illinois:** a Box Plus/Minus estimate — how much will this player help or hurt per 100 possessions in a Big Ten rotation. Zero is an average Big Ten starter. Positive is a contributor. Negative is a liability.

The model is an ensemble of three approaches working together. A Random Forest (400 decision trees that each look at a random slice of the data and vote), an XGBoost model (which corrects its own errors iteratively and tends to be the most accurate on structured stat data like this), and a neural network with three layers. The three outputs get combined into one weighted score. Using three models together is more accurate than relying on any single one.

To train it, I needed thousands of examples of transfers that worked and transfers that didn't. That verified dataset doesn't exist publicly, so I built 3,000 synthetic profiles calibrated to real NCAA statistical distributions. The model architecture is real. The training data quality is prototype-level and is labeled as such throughout the app.

Tested on data the model had never seen, it correctly separated likely contributors from busts 88% of the time.

One thing the model learned on its own: the conference jump matters a lot. A player moving from the Sun Belt to the Big Ten gets penalized automatically because the data shows that production almost always drops in that scenario. This is not a hardcoded rule — it's something the model picked up from the training examples.

The Transfer Success Predictor page shows every player's scores plus a breakdown of exactly which stats drove the prediction, so a coach can look at it and decide whether to trust it or push back.

---

## Why It's Useful to a Coaching Staff

The platform doesn't make the call — the coaches do. What it changes is how long it takes to get to a well-informed decision.

A recruiting coordinator building a portal board manually is pulling from BartTorvik, running fit scores in Excel, writing a summary, and cross-referencing film notes. That takes hours. This does it before you finish asking the question.

Every score is explainable. The Illinois Fit Score tells you exactly which stats pushed a player up or down. The prediction model shows you the top drivers for each individual player. When a coach pushes back on a number, you can show them why the model landed where it did.

The Hidden Gem Lab creates a real competitive edge. A player sitting at rank 80 in public attention who the model puts in the top 15 by fit and production is a player Illinois can move on before other programs notice. That window is days, not weeks.

And the scouting report generates in seconds and exports as a PDF. No writing from scratch. Pull and send.

---

## Data

**Player stats:** 200 real D1 players, 2024-25 season, scraped from Sports Reference and BartTorvik using Python. Sports Reference was scraped directly with requests. BartTorvik uses Cloudflare protection so I used Playwright (a browser automation tool) to load the page like a real user and pull the data. Covers the Big Ten, SEC, Big 12, and ACC.

**Illinois roster:** 2024-25 season data from BartTorvik. Jakucionis, T. Ivisic, Will Riley, Kylan Boswell, Tre White, and others.

**Portal eligibility:** These are 2024-25 season stats used to model how a player's production would translate if they transferred. Not every player has entered the portal.

**Prediction model training data:** 3,000 synthetic profiles calibrated to real NCAA statistical distributions. Labeled as synthetic throughout the app.

---

## Pages

| Page | What it does |
|---|---|
| `/` | Chat home, routes your question to the right mode |
| `/recruiting-center` | Tiered board: Tier 1 targets, role shortlists, risk flags |
| `/transfer-success-predictor` | Prediction score and projected impact for any player |
| `/player-intelligence` | Full player profile, radar chart, closest statistical comparables |
| `/hidden-gem-lab` | Players the model rates higher than their public ranking |
| `/compare-players` | Side-by-side comparison with a recommendation |
| `/roster-builder` | Current roster, depth chart, positional gaps |
| `/scouting-center` | Scouting report generator with PDF export |
| `/front-office-insights` | Insight cards generated from the current player board |

---

## Setup

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
# http://localhost:8000
```

**Frontend**
```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
# http://localhost:3000
```

All environment variables are optional. `GEMINI_API_KEY` powers the open-ended chat but the app works without it. `FRONTEND_ORIGIN` defaults to `http://localhost:3000` and `NEXT_PUBLIC_API_BASE_URL` defaults to `http://localhost:8000/api`.

---

## Tech Stack

Frontend: Next.js 15, TypeScript, TailwindCSS, Plotly.js. Backend: FastAPI, Python 3.12, SQLite. Prediction model: scikit-learn and XGBoost. Chat: Google Gemini 1.5 Flash (optional). PDF export: ReportLab. Data processing: pandas and NumPy.

---

## Notes

The prediction model is trained on synthetic data so treat scores as directional, not definitive. Player data is a 2024-25 snapshot and portal eligibility is not tracked.
