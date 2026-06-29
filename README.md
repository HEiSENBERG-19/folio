# Folio

A lightweight, single-user stock portfolio tracker with weighted average cost (WAC) P&L accounting and automated charting via yfinance.

This codebase is designed to be built and maintained entirely by AI agents under human supervision.

## Getting Started

### 🤖 AI Agents
If you are an AI agent starting a new session on this repository, please read [AGENTS.md](AGENTS.md) first. It contains the permanent context layer, system architecture summaries, coding conventions, and the current roadmap status.

### 👤 Humans
To run the project locally once built:

#### Backend
1. Navigate to the `backend/` directory.
2. Initialize virtual environment: `python -m venv .venv` and activate it.
3. Install dependencies: `pip install -r requirements.txt`
4. Run the API server: `uvicorn app.main:app --reload`

#### Frontend
1. Navigate to the `frontend/` directory.
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`
