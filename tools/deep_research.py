"""Runs ONE TradingAgents analysis and writes the reports to a JSON file. This file runs inside TradingAgents' own
Python environment (not Tuned in Markets's), started by deep.py:
    <tradingagents python> tools/deep_research.py TICKER YYYY-MM-DD out.json"""
import json
import sys
import traceback

ticker, date, out = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    config = DEFAULT_CONFIG.copy()
    ta = TradingAgentsGraph(debug=False, config=config)
    state, decision = ta.propagate(ticker, date)
    inv, risk = state.get("investment_debate_state") or {}, state.get("risk_debate_state") or {}
    res = {"ok": True, "ticker": ticker, "date": date, "decision": decision, "final": state.get("final_trade_decision"),
           "reports": {"Market analyst": state.get("market_report"), "Sentiment analyst": state.get("sentiment_report"),
                       "News analyst": state.get("news_report"), "Fundamentals analyst": state.get("fundamentals_report")},
           "debate": {"Bull case": inv.get("bull_history"), "Bear case": inv.get("bear_history"), "Research manager": inv.get("judge_decision")},
           "plan": {"Trader's plan": state.get("trader_investment_plan")},
           "risk": {"Aggressive": risk.get("aggressive_history"), "Conservative": risk.get("conservative_history"),
                    "Neutral": risk.get("neutral_history"), "Risk judge": risk.get("judge_decision")}}
except Exception as e:
    res = {"ok": False, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
open(out, "w").write(json.dumps(res, default=str))
