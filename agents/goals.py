from typing import Tuple
from datetime import date
from orchestrator.tools import update_goal_progress, suggest_starter_goals
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)
    
class Agent:
    name = "Goal Agent"

    def step(self, state) -> Tuple[object, str]:
        if not state.goals:
            state.goals = suggest_starter_goals(state)
            names = ", ".join(g["name"] for g in state.goals)
            msg = f"Created starter goals: {names}."
            return state, msg

        state.goals = update_goal_progress(state)
        active = [g for g in state.goals if g.get("target") and g.get("saved") is not None]
        if active:
            top = active[0]
            pct = 0 if top["target"] == 0 else int(100 * top["saved"] / top["target"])
            deadline = top.get("deadline", str(date.today()))
            msg = f"Updated goals. Closest: **{top['name']}** at {pct}% (by {deadline})."
        else:
            msg = "Updated goals."
        return state, msg
