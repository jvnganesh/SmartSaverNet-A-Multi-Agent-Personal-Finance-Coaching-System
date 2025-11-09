from typing import Tuple
from orchestrator.tools import generate_advice
# from orchestrator.state import UserState
# if isinstance(state, dict):
#     state = UserState(**state)

class Agent:
    name = "Advice Agent"

    def step(self, state) -> Tuple[object, str]:
        # In production, this can call an LLM with guardrails.
        msg = generate_advice(state)
        return state, msg
