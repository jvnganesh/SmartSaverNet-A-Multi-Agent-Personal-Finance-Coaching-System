# agents/debt.py
from typing import Tuple
from orchestrator.tools import payoff_plan  # builds an ordered plan and summary given debts + method
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)

class Agent:
    """
    Debt Agent
    - Chooses a payoff strategy (avalanche/snowball) from state.debt_strategy.
    - Produces a next-action focus and high-level timeline.
    Protocol: step(state) -> (state, message:str)
    """
    name = "Debt Agent"

    def step(self, state) -> Tuple[object, str]:
        # state.debts: [{name, balance, apr, min_payment}]
        # state.debt_strategy: "avalanche" | "snowball"
        plan = payoff_plan(state.debts, method=getattr(state, "debt_strategy", "avalanche"))
        state.debt_plan = plan

        # Expecting plan like:
        # {
        #   "method": "avalanche",
        #   "next_focus": {"name": "...", "extra_payment": 3000},
        #   "order": [{"name": "...", "months": 5}, ...],
        #   "projected_interest_saved": 12345.67
        # }
        focus = plan.get("next_focus") or {}
        focus_name = focus.get("name", "N/A")
        extra = focus.get("extra_payment")
        extra_txt = f" with extra ₹{extra:,}" if isinstance(extra, (int, float)) else ""

        interest_saved = plan.get("projected_interest_saved")
        saved_txt = (
            f" Est. interest saved ₹{round(float(interest_saved)):,}."
            if isinstance(interest_saved, (int, float)) else ""
        )

        msg = (
            f"Using {plan.get('method', 'avalanche')} method. "
            f"Next focus: {focus_name}{extra_txt}.{saved_txt}"
        )

        return state, msg
