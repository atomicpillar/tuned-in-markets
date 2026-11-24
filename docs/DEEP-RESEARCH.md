# Deep research with TradingAgents

The "Deep research" button under a stock's research note runs [TradingAgents](https://github.com/TauricResearch/TradingAgents)
(Apache-2.0): a team of AI analysts (market, sentiment, news, fundamentals), a bull and a bear researcher, a trader and a risk team
debate the stock and write a decision with reasons. Tuned in Markets does the fast, free scanning; this is the slow second stage for the few
stocks worth a close look. It runs on your computer with your own AI account. The output is a model's opinion for research, not advice.

## One-time setup (about 5 minutes)
1. Install it into its own folder and Python environment (it does not touch Tuned in Markets):
   - **Mac:**
     ```bash
     cd ~/Downloads/tuned-in-markets-main
     bash tools/setup_deep_research.sh
     ```
   - **Windows:** install [Git for Windows](https://git-scm.com/download/win), then double-click `tools\setup_deep_research.bat`.
   It installs release v0.3.1 from the authors' own repository.
2. Copy `.env.example` to `.env` in the `tuned-in-markets` folder and fill in your OpenAI key (`OPENAI_API_KEY`). The model lines are already set to TradingAgents' own defaults.
   `.env` is git-ignored. Never paste the keys in chat or commit them.
   The installer already made `.env` for you. Mac: `open -e .env`. Windows: right-click `.env`, Open with, Notepad. Find the line `OPENAI_API_KEY=` and paste your key after the equals sign. Save.
   Never paste a key into a chat, a screenshot or a GitHub issue.
3. Restart Tuned in Markets (`bash run.sh`, or `run.bat` on Windows). Open any stock's chart: the Deep research box appears under the research note.

## Models and cost
- **Measured:** one in-depth run on a large US stock with `gpt-5.4-mini` on both model lines cost **about 15 cents** on OpenAI's usage page. That is the benchmark to expect from the default setup, and it takes 5 to 15 minutes.
- **Bigger models cost more.** The sample `.env.example` puts a larger model on the debates and decisions. It gives deeper reasoning at a higher price. Check your OpenAI usage page after the first run, then decide.
- **Cheaper still:** fewer debate rounds (`TRADINGAGENTS_MAX_DEBATE_ROUNDS=1`) and the small model on both lines.
- **Prices change.** Check your provider's pricing page rather than relying on any number written here.
- **You pay the provider directly.** An API key is billed per use and is separate from a ChatGPT or Claude subscription.

A run takes a few minutes. `TRADINGAGENTS_MAX_DEBATE_ROUNDS=1` keeps it cheap and fast. One result is kept per stock per day in `data/deep/`.

## Markets
India stocks run as `SYMBOL.NS` (for example `RELIANCE.NS`); US stocks run as their plain ticker. TradingAgents gets its own prices and news
from Yahoo, so it can disagree slightly with the prices on the dashboard.

## What you get

A rated decision from Sell to Buy, where the analysts, trader and risk team land, each analyst's stance, the bull case against the bear case, the trader's plan and the risk views, laid out as cards. **Download report** saves the whole report as a single page (opens offline) and **Download as Markdown** saves plain text, so you can keep it.
