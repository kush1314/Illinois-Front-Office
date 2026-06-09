# Illinois Front Office

A web platform for evaluating transfer portal targets, built for the Illinois Men's Basketball Analytics Internship.

When a player enters the portal, a staff may have 48 hours to decide whether to pursue him. The information needed to do that sits across BartTorvik, Sports Reference, spreadsheets, and film notes with nothing connecting them. This pulls it into one workflow.

---

## What It Does

You type a question in plain English and get a structured answer. The platform has 12 modes, each covering a different step of the same decision: should Illinois pursue this player?

- **Find targets:** recruiting board tiered by fit and risk, tuned to Underwood's system
- **Evaluate production:** prediction model estimates how likely a player is to succeed at Illinois
- **Check system fit:** scores players against Illinois's specific requirements (3-point shooting, switching defense, low turnovers)
- **Compare options:** side-by-side comparison of two players with a recommendation
- **Find overlooked value:** flags players whose stats rank them higher than their public attention suggests
- **Check roster impact:** simulates what adding a player does to the depth chart
- **Summarize and share:** scouting report exportable as a PDF

The chat uses Google Gemini when you have an API key. Without one everything still works.

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

## Data

**Player stats:** 200 real D1 players, 2024-25 season, scraped from Sports Reference and BartTorvik using Python. Sports Reference was scraped directly with requests. BartTorvik uses Cloudflare protection so I used Playwright (a browser automation tool) to load the page like a real user and pull the data. Covers the Big Ten, SEC, Big 12, and ACC.

**Illinois roster:** 2024-25 season data from BartTorvik. Jakucionis, T. Ivisic, Will Riley, Kylan Boswell, Tre White, and others.

**Portal eligibility:** These are 2024-25 season stats used to model how a player's production would translate if they transferred. Not every player has entered the portal.

**Prediction model training data:** Building the model required examples of past transfers and what happened to a player's stats afterward. That dataset doesn't exist publicly in a clean format, so I built 3,000 synthetic profiles calibrated to real NCAA statistical distributions. The training data is synthetic; the model architecture and prediction logic are real. This is labeled throughout the app.

---

## Prediction Model

Takes 16 stats per player including shooting efficiency, usage, ball-handling, rebounding, defensive impact, and conference jump size, and outputs two things:

1. A success probability (0-100): how likely is this transfer to work out
2. A projected BPM at Illinois: how much impact to expect

Tested on data the model never trained on, it correctly separated likely contributors from busts 88% of the time. The conference jump is one of the strongest signals the model learned. Moving from the Sun Belt to the Big Ten gets penalized automatically.

The Transfer Success Predictor page shows exactly which stats drove each player's score.

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
