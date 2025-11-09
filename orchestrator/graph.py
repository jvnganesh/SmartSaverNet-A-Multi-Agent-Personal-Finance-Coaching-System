# orchestrator/graph.py
from __future__ import annotations

import importlib
import traceback
from typing import Dict, List, Any

from langgraph.graph import StateGraph, END
from orchestrator.state import UserState


def _load_agent_module(name: str):
    try:
        return importlib.import_module(f"agents.{name}")
    except Exception as e:
        raise ImportError(f"Failed to import agents.{name}: {e}")

def _make_node(mod):
    if not hasattr(mod, "Agent"):
        raise AttributeError(f"Module {mod.__name__} has no 'Agent' class")

    def node(payload: Dict[str, Any]) -> Dict[str, Any]:
        agent = mod.Agent()
        try:
            state = payload["user_state"]
            # we expect `state` to already be a UserState
            if not isinstance(state, UserState):
                raise TypeError("user_state is not a UserState (check how you built the graph payload)")
            new_state, msg = agent.step(state)
            payload["user_state"] = new_state
            payload["messages"].append({"agent": agent.name, "content": msg})
        except Exception as e:
            tb = traceback.format_exc(limit=2)
            payload["messages"].append({
                "agent": getattr(agent, "name", mod.__name__),
                "content": f"⚠️ Error: {type(e).__name__}: {e}\n{tb}"
            })
        return payload
    return node


def build_graph(active_agents: List[str]):
    graph = StateGraph(state_schema=dict)  # payload is a dict carrying the UserState

    if not active_agents:
        def noop(payload: Dict[str, Any]) -> Dict[str, Any]:
            return payload
        graph.add_node("noop", noop)
        graph.set_entry_point("noop")
        return graph.compile()

    prev = None
    for name in active_agents:
        mod = _load_agent_module(name)
        node_fn = _make_node(mod)
        graph.add_node(name, node_fn)
        if prev is None:
            graph.set_entry_point(name)
        else:
            graph.add_edge(prev, name)
        prev = name

    graph.add_edge(prev, END)
    return graph.compile()


def run_graph_once(compiled_graph, state: UserState):
    if not isinstance(state, UserState):
        raise TypeError("run_graph_once expected a UserState instance")
    payload = {"user_state": state, "messages": []}
    out = compiled_graph.invoke(payload)
    return out["user_state"], out["messages"]



# # orchestrator/graph.py
# from __future__ import annotations

# import importlib
# from typing import Dict, List, Any, Callable

# from langgraph.graph import StateGraph, END
# from orchestrator.state import UserState


# def _load_agent_module(name: str):
#     """
#     Import agents.<name> and return its module.
#     Expects a class `Agent` with:
#       - name: str
#       - step(self, state: UserState) -> tuple[UserState, str]
#     """
#     return importlib.import_module(f"agents.{name}")


# def _make_node(mod):
#     """
#     Wrap an Agent().step into a LangGraph node that:
#       - mutates the UserState
#       - appends a user-friendly message
#     """
#     def node(payload: Dict[str, Any]) -> Dict[str, Any]:
#         # payload carries {"user_state": UserState, "messages": List[Dict]}
#         agent = getattr(mod, "Agent")()
#         try:
#             new_state, msg = agent.step(payload["user_state"])
#             payload["user_state"] = new_state
#             payload["messages"].append({"agent": agent.name, "content": msg})
#         except Exception as e:
#             # Fail-safe so one agent doesn't crash the whole run
#             payload["messages"].append({
#                 "agent": getattr(agent, "name", mod.__name__),
#                 "content": f"⚠️ Error: {type(e).__name__}: {e}"
#             })
#         return payload
#     return node


# def build_graph(active_agents: List[str]) -> Any:
#     """
#     Build a simple linear LangGraph pipeline in the order of active_agents.
#     Returns a compiled graph ready to invoke().
#     """
#     graph = StateGraph(state_schema=dict)  # payload is a plain dict

#     # If no agents enabled, create a no-op graph
#     if not active_agents:
#         def noop(payload: Dict[str, Any]) -> Dict[str, Any]:
#             return payload
#         graph.add_node("noop", noop)
#         graph.set_entry_point("noop")
#         return graph.compile()

#     # Create a node per agent
#     previous_name = None
#     for name in active_agents:
#         mod = _load_agent_module(name)
#         node_fn = _make_node(mod)
#         graph.add_node(name, node_fn)

#         if previous_name is None:
#             graph.set_entry_point(name)
#         else:
#             graph.add_edge(previous_name, name)

#         previous_name = name

#     # End after the last one
#     graph.add_edge(previous_name, END)

#     return graph.compile()


# def run_graph_once(compiled_graph: Any, state: UserState):
#     """
#     Execute the compiled graph ONE pass and return (new_state, messages).
#     """
#     start_payload = {
#         "user_state": state,
#         "messages": []  # will be filled by agents
#     }
#     result = compiled_graph.invoke(start_payload)
#     return result["user_state"], result["messages"]
