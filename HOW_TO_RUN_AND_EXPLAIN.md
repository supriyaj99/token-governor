# TokenGovernor — How to Run It & How to Explain It

Two parts: **Part A** is the click-by-click guide to run it on your computer.
**Part B** is exactly what to say when someone asks you about it (interviews,
recruiters, your resume). Keep this file; it's your cheat sheet.

---

# PART A — How to run it

## What you need installed (one time)
- **Python** (3.10 or newer) — https://www.python.org/downloads/ — during install,
  tick **"Add Python to PATH"**.
- **VS Code** (the editor) — https://code.visualstudio.com/
- Docker is **optional** — you do NOT need it for the quick path below.

## The fastest path (no Docker, ~5 minutes)

1. **Unzip** the project somewhere simple, e.g. `Documents\tokengovernor`.

2. **Open the folder in VS Code:** File → Open Folder → pick `tokengovernor`.

3. **Open a terminal inside VS Code:** menu **Terminal → New Terminal**. A box
   opens at the bottom. You'll type the next commands there, one at a time.

4. **Create a private sandbox for this project's libraries** (so they don't mess
   with anything else on your PC):
   ```powershell
   python -m venv .venv
   ```

5. **Turn the sandbox on:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   Your prompt now starts with `(.venv)`.
   *If it errors about "running scripts is disabled,"* run this once, then redo step 5:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```

6. **Install the libraries:**
   ```powershell
   pip install -r requirements.txt
   ```
   (Takes a minute or two. It's downloading FastAPI, Streamlit, etc.)

7. **Tell it to use a simple local database + free mock mode, then start the server:**
   ```powershell
   $env:DATABASE_URL="sqlite:///./tokengov.db"
   $env:MOCK_MODE="true"
   uvicorn app.main:app --reload
   ```
   **It worked when** you see `Uvicorn running on http://127.0.0.1:8000`.
   Leave this terminal running.

## Now actually see it work

Open a **second** terminal (Terminal → New Terminal) and turn the sandbox on
again (`.\.venv\Scripts\Activate.ps1`). Then:

```powershell
python -m rag.seed_traffic 300
```
This sends 300 pretend requests from three teams. Now visit these in your browser:

- **http://localhost:8000/docs** — try the API yourself (click a route → "Try it out").
- **http://localhost:8000/stats** — total spend vs budget, average quality.
- **http://localhost:8000/router** — what the router has *learned* so far.
- **http://localhost:8000/governance** — the self-governing loop: the budget
  forecast plus which teams get tightened and why.

## See the pretty dashboard
- **Instant, no install:** double-click `dashboard/preview.html` — opens in your browser.
- **Live data version:** in a terminal (sandbox on), run:
  ```powershell
  streamlit run dashboard/streamlit_app.py
  ```

## Get your headline number (the benchmark)
```powershell
python -m benchmark.run_benchmark
```
Prints the cost savings, the trade-off curve, and the learning curve. (Already
saved in `BENCHMARK_RESULTS.md`.)

## Run the tests (proves it works)
```powershell
python -m pytest -q
```

## If something breaks
- **`python` not recognized** → Python wasn't added to PATH; reinstall and tick that box.
- **`column ... does not exist` / database errors** → delete the `tokengov.db`
  file and start the server again (it rebuilds the table).
- **Port 8000 already in use** → close the other thing using it, or run
  `uvicorn app.main:app --reload --port 8001` and use 8001 in the URLs.
- **Any red error you don't understand** → copy the exact text and ask; errors
  are normal and each has a specific fix.

---

# PART B — How (and when) to explain it

You'll explain this in three situations: a **resume bullet**, a **30-second
pitch** (recruiter screen / "tell me about a project"), and a **2-minute deep
dive** (technical interview). Here's each, ready to use.

## The resume bullet (fill in your live URL once deployed)
> Built & deployed **TokenGovernor**, a cost-aware LLM gateway: a Thompson-sampling
> router picks the cheapest model that clears a measured quality bar, a forecaster
> auto-tightens policy before budget exhaustion, and a value-weighted layer
> throttles low-value spend first. **~47% cheaper than top-tier-only at near-equal
> quality** on a 6,000-request reproducible benchmark. FastAPI · PostgreSQL/
> TimescaleDB · Docker · Streamlit.

## The 30-second pitch (memorize the shape, say it in your words)
> "Companies burn through their AI budget in a few months because nothing checks
> whether the expensive model was even needed for each request. I built
> TokenGovernor — it sits in front of the AI models, and for every request it
> figures out the cheapest model that's still good enough, predicts when the
> budget will run out, and tightens its own spending rules before the money's
> gone. In my benchmark it cut cost about 47% with almost no quality loss."

## The 2-minute deep dive — structure: PROBLEM → SYSTEM → ONE DEEP PART
1. **Problem** (the 30-sec pitch above).
2. **System** — walk the request through the six modules:
   - "Every request hits my **gateway**, which logs cost, tokens, and quality."
   - "A **classifier** labels the task and how complex it is."
   - "A **quality estimator** scores each answer cheaply, so I can tell if a
     cheap model was good enough — without paying a big model to grade everything."
   - "A **Thompson-sampling router** learns, per task type, the cheapest model
     that clears the quality bar."
   - "A **forecaster** predicts budget exhaustion and a **controller** auto-tightens."
   - "And a **value-weighted fairness layer** — the part I'm proudest of —
     tightens the teams whose spending produces poor results first, and protects
     the high-value teams."
3. **One deep part** — pick the router or the fairness layer and go deeper (see
   the one-liners and Q&A below).

## One-line answer for "what does each module do"
- **Gateway:** intercepts and records every request (cost, tokens, latency, quality).
- **Classifier:** predicts task type + complexity before any model is called.
- **Quality estimator:** a cheap 0–1 score of each answer (relevance, format, etc.).
- **Router:** a contextual bandit that learns the cheapest good-enough model.
- **Forecaster + controller:** predicts budget exhaustion and tightens policy on its own.
- **Fairness layer:** tightens low-value-per-dollar spenders first; protects high-value ones.

## The hard questions (and honest answers)
- **"Why not just use LiteLLM / Portkey?"**
  > "I do — LiteLLM is the provider layer inside my gateway. I built the parts it
  > doesn't: the learning router, the quality-evaluation loop, and the
  > forecast-driven controller. I built them myself specifically to understand
  > routing and cost governance deeply."
- **"Is this a novel idea?"**
  > "The category exists and is crowded — I'm not claiming I invented it. I built
  > a working version to understand it, and I took one part further than the
  > existing tools: tightening budget by *measured value*, not just by spend."
- **"How do you measure quality without it being expensive?"**
  > "Cheap implicit signals first — did it answer, is it on-topic, right format.
  > For a real system you'd add a small trained scorer and only send a *sample*
  > of responses to a big LLM judge, so you're not paying to grade everything."
- **"Why a bandit instead of fixed rules?"**
  > "A hand-written rule works until models and prices change, then you rewrite
  > the thresholds. The bandit keeps learning from real outcomes automatically.
  > In my benchmark it matched a good hand rule and approached the theoretical best."
- **"What's the result?"**
  > "On a 6,000-request reproducible benchmark it was ~47% cheaper than always
  > using the top model, within ~6 points of its quality, and tunable from 36% to
  > 62% savings with one knob. I compared against baselines and an oracle so it's
  > not cherry-picked."

## The golden rule of explaining it
Be honest and specific. Don't oversell it as revolutionary — that's a red flag to
people who know the field. Framing it as *"I built a working version of a real
system to understand it deeply, and went further on one hard part"* is the
strongest, most credible thing you can say. Owning the trade-offs (e.g. "the
learned router is close to a hand rule, but it adapts automatically") signals
senior-level judgment.
