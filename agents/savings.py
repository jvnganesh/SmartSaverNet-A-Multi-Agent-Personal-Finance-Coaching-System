# agents/savings.py
from typing import Tuple
from orchestrator.tools import find_micro_savings  # returns a list of tips [{'tip': str, 'est_saving': float}, ...]
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)

class Agent:
    """
    Savings Agent
    - Surfaces tiny, low-friction saving opportunities (subscriptions, fees, better bill plans).
    - Suggests an auto-transfer amount based on current savings_rate.
    Protocol: step(state) -> (state, message:str)
    """
    name = "Savings Agent"

    def step(self, state) -> Tuple[object, str]:
        ideas = find_micro_savings(state)  # safe to call with empty txns; returns []
        state.savings_suggestions = ideas

        # Suggest a simple, fixed-date auto-transfer (1st of month) from checking → savings.
        monthly_income = float(state.income)  # treated as monthly in the UI
        suggested_autosave = round(monthly_income * float(state.savings_rate))

        # Friendly one-liner for the UI feed
        if ideas:
            example = ideas[0]["tip"]
            msg = (
                f"Found {len(ideas)} micro-savings (e.g., “{example}”). "
                f"Recommend auto-transfer of ₹{suggested_autosave:,} on the 1st each month."
            )
        else:
            msg = (
                f"No obvious waste detected. Still recommend auto-transfer of "
                f"₹{suggested_autosave:,} on the 1st each month."
            )

        # (Optional) You can stash this suggestion on state for other agents (e.g., Goals)
        setattr(state, "suggested_autosave", suggested_autosave)
        return state, msg
