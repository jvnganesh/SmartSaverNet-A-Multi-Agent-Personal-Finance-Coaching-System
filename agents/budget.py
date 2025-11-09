# agents/budget.py
from __future__ import annotations

from typing import Tuple, Dict
import logging

from orchestrator.state import UserState
from orchestrator.tools import calc_budget  # you’ll implement this next
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)


logger = logging.getLogger(__name__)


def _fmt_inr(x: float) -> str:
    """Format a number as INR with commas (no decimals)."""
    try:
        return f"₹{x:,.0f}"
    except Exception:  # very defensive; avoid crashing the UI
        return f"₹{x}"


class Agent:
    """
    Budget Agent
    ------------
    Responsibilities:
      - Compute a simple, followable monthly budget (essentials / wants / savings)
      - Update state.budget and state.savings_rate
      - Return a short, friendly message for the UI activity feed
    """
    name = "Budget Agent"

    def step(self, state: UserState) -> Tuple[UserState, str]:
        # Delegate core math/logic to shared tools so it’s testable & reusable
        try:
            budget: Dict[str, float] = calc_budget(state)
        except Exception as e:
            logger.exception("calc_budget failed; falling back to 50/30/20 heuristic.")
            income = max(float(state.income or 0.0), 0.0)
            # Fallback heuristic
            budget = {
                "essentials": income * 0.50,
                "wants": income * 0.30,
                "savings": income * 0.20,
            }

        # Persist on state
        state.budget = budget

        income = float(state.income or 0.0)
        savings = float(budget.get("savings", 0.0))
        state.savings_rate = (savings / income) if income > 0 else 0.0

        # Friendly, compact summary for the UI
        msg = (
            f"Set your monthly budget → "
            f"Essentials {_fmt_inr(budget.get('essentials', 0))}, "
            f"Wants {_fmt_inr(budget.get('wants', 0))}, "
            f"Savings {_fmt_inr(savings)} "
            f"({state.savings_rate:.0%})."
        )
        return state, msg
