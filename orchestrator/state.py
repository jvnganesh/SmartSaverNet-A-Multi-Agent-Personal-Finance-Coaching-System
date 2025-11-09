# orchestrator/state.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
# If you have pydantic>=2.4, this is optional; leaving config minimal avoids serializer issues.

class UserState(BaseModel):
    suggested_autosave: Optional[float] = Field(
        default=None, 
        description="The recommended amount for automated savings transfer, set by the Savings Agent."
    )
    # Monthly snapshot (INR)
    income: float = 60_000.0
    monthly_spend: float = 45_000.0
    savings_rate: float = 0.15  # 0..1

    # Agent-populated fields
    budget: Dict[str, float] = Field(default_factory=dict)
    savings_suggestions: List[Dict[str, Any]] = Field(default_factory=list)

    # Debts
    debts: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"name": "Credit Card", "balance": 30_000.0, "apr": 0.36, "min_payment": 1_500.0},
            {"name": "Student Loan", "balance": 120_000.0, "apr": 0.11, "min_payment": 2_500.0},
        ]
    )
    debt_strategy: str = "avalanche"
    debt_plan: Dict[str, Any] = Field(default_factory=dict)

    # Goals & alerts
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[Dict[str, Any]] = Field(default_factory=list)

def default_state() -> UserState:
    return UserState()


# # orchestrator/state.py
# from __future__ import annotations

# from typing import List, Dict, Any
# from pydantic import BaseModel, Field, field_validator, ConfigDict


# class UserState(BaseModel):
#     """
#     Canonical state object shared by all agents and the graph.
#     Keep this lightweight and serializable.
#     """
#     # Pydantic v2 config
#     model_config = ConfigDict(
#         ser_json_inf_nan=True,  # tolerate inf/nan in JSON
#         frozen=False,           # allow in-place mutation by agents
#     )

#     # Income & spend snapshot (monthly, INR)
#     income: float = 60_000.0
#     monthly_spend: float = 45_000.0
#     savings_rate: float = 0.15  # fraction of income auto-saved

#     # Agent-populated fields
#     budget: Dict[str, float] = Field(default_factory=dict)  # {"essentials":..., "wants":..., "savings":...}
#     savings_suggestions: List[Dict[str, Any]] = Field(default_factory=list)

#     # Debts
#     debts: List[Dict[str, Any]] = Field(
#         default_factory=lambda: [
#             {"name": "Credit Card", "balance": 30_000, "apr": 0.36, "min_payment": 1_500},
#             {"name": "Student Loan", "balance": 120_000, "apr": 0.11, "min_payment": 2_500},
#         ]
#     )
#     debt_strategy: str = "avalanche"  # or "snowball"
#     debt_plan: Dict[str, Any] = Field(default_factory=dict)

#     # Goals
#     goals: List[Dict[str, Any]] = Field(default_factory=list)

#     # Alerts
#     alerts: List[Dict[str, Any]] = Field(default_factory=list)

#     # ---- Validators (basic sanity) ----
#     @field_validator("income", "monthly_spend")
#     @classmethod
#     def non_negative(cls, v: float) -> float:
#         return max(0.0, float(v))

#     @field_validator("savings_rate")
#     @classmethod
#     def clamp_rate(cls, v: float) -> float:
#         # keep within [0, 1]
#         return min(1.0, max(0.0, float(v)))


# def default_state() -> UserState:
#     """Factory to create a fresh state with safe defaults."""
#     return UserState()

# # # orchestrator/state.py
# # from __future__ import annotations

# # from typing import List, Dict, Any
# # from pydantic import BaseModel, Field, field_validator


# # class UserState(BaseModel):
# #     """
# #     Canonical state object shared by all agents and the graph.
# #     Keep this lightweight and serializable.
# #     """
# #     # Income & spend snapshot (monthly, INR)
# #     income: float = 60_000.0
# #     monthly_spend: float = 45_000.0
# #     savings_rate: float = 0.15  # fraction of income auto-saved

# #     # Agent-populated fields
# #     budget: Dict[str, float] = Field(default_factory=dict)  # {"essentials":..., "wants":..., "savings":...}
# #     savings_suggestions: List[Dict[str, Any]] = Field(default_factory=list)

# #     # Debts
# #     debts: List[Dict[str, Any]] = Field(
# #         default_factory=lambda: [
# #             {"name": "Credit Card", "balance": 30_000, "apr": 0.36, "min_payment": 1_500},
# #             {"name": "Student Loan", "balance": 1_20_000, "apr": 0.11, "min_payment": 2_500},
# #         ]
# #     )
# #     debt_strategy: str = "avalanche"  # or "snowball"
# #     debt_plan: Dict[str, Any] = Field(default_factory=dict)

# #     # Goals
# #     goals: List[Dict[str, Any]] = Field(default_factory=list)

# #     # Alerts
# #     alerts: List[Dict[str, Any]] = Field(default_factory=list)

# #     # ---- Validators (basic sanity) ----
# #     @field_validator("income", "monthly_spend")
# #     @classmethod
# #     def non_negative(cls, v: float) -> float:
# #         return max(0.0, float(v))

# #     @field_validator("savings_rate")
# #     @classmethod
# #     def clamp_rate(cls, v: float) -> float:
# #         # keep within [0, 1]
# #         return min(1.0, max(0.0, float(v)))

# #     model_config = {
# #         "ser_json_inf_nan": True,     # tolerant serialization
# #         "frozen": False,              # allow in-place mutation by agents
# #     }


# # def default_state() -> UserState:
# #     """
# #     Factory to create a fresh state with safe defaults.
# #     """
# #     return UserState()
