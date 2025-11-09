from typing import Tuple
from orchestrator.tools import detect_overspend_alerts
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)

class Agent:
    name = "Spending Alert Agent"

    def step(self, state) -> Tuple[object, str]:
        alerts = detect_overspend_alerts(state)
        state.alerts = alerts
        msg = f"{len(alerts)} alert(s) this period." if alerts else "No overspending detected. ✅"
        return state, msg
