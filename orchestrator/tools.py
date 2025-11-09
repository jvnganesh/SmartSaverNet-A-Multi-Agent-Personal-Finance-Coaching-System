# orchestrator/tools.py
from __future__ import annotations

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# ---- Simple domain defaults / policies ----
DEFAULT_BUDGET_RULE = {
    "essentials": 0.50,  # rent, groceries, utilities
    "wants": 0.30,       # dining out, shopping
    "savings": 0.20,     # emergency fund, investments, debt-prepayment
}

DEFAULT_CATEGORY_LIMITS = {
    # % of income (soft guidance; alerts trigger if exceeded by much)
    "groceries": 0.12,
    "dining": 0.08,
    "shopping": 0.07,
    "transport": 0.06,
    "entertainment": 0.05,
}

# ---- Helpers ----
def inr(n: float) -> str:
    """Format rupees with thousands separators."""
    return f"₹{n:,.0f}"

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

# ---- Budgeting ----
def calc_budget(state) -> Dict[str, float]:
    """
    Compute a simple envelope budget from income and a target savings rate.
    If user's savings_rate is provided, bias the split towards that.
    """
    income = float(getattr(state, "income", 0.0))
    savings_rate = clamp(float(getattr(state, "savings_rate", 0.20)), 0.0, 0.9)

    # Start with defaults and adjust savings slice toward user preference.
    essentials_ratio = DEFAULT_BUDGET_RULE["essentials"]
    wants_ratio = DEFAULT_BUDGET_RULE["wants"]
    savings_ratio = savings_rate

    # Rebalance the remaining (1 - savings) between essentials:wants ~ 5:3
    remain = max(0.0, 1.0 - savings_ratio)
    total_default_non_sav = DEFAULT_BUDGET_RULE["essentials"] + DEFAULT_BUDGET_RULE["wants"]
    essentials_ratio = remain * (DEFAULT_BUDGET_RULE["essentials"] / total_default_non_sav)
    wants_ratio = remain * (DEFAULT_BUDGET_RULE["wants"] / total_default_non_sav)

    budget = {
        "essentials": round(income * essentials_ratio, 2),
        "wants": round(income * wants_ratio, 2),
        "savings": round(income * savings_ratio, 2),
    }
    return budget

# ---- Micro-savings ideas ----
def find_micro_savings(state) -> List[Dict[str, Any]]:
    """
    Produce small, actionable saving ideas.
    In a real app, this would inspect recent transactions/subscriptions.
    """
    income = float(getattr(state, "income", 0.0))
    monthly_spend = float(getattr(state, "monthly_spend", 0.0))
    pressure = clamp((monthly_spend - 0.9 * income) / max(income, 1.0), 0, 0.5)

    ideas = [
        {"tip": "Round-up transfers: auto-save spare change from each txn", "est_monthly_savings": 300},
        {"tip": "Switch to a lower-cost mobile/data plan", "est_monthly_savings": 250},
        {"tip": "Cancel one unused subscription", "est_monthly_savings": 400},
        {"tip": "Buy staples in bulk (rice, lentils, oil)", "est_monthly_savings": 200},
        {"tip": "Shift dining-out to once a week", "est_monthly_savings": 600},
    ]

    # If spending pressure is high, surface stronger ideas first
    ideas.sort(key=lambda x: -x["est_monthly_savings"] * (1 + pressure))
    return ideas[:5]

# ---- Debt payoff planning ----
@dataclass
class Debt:
    name: str
    balance: float
    apr: float       # as decimal, e.g., 0.24
    min_payment: float

def _normalize_debts(debts_in: List[Dict[str, Any]]) -> List[Debt]:
    out: List[Debt] = []
    for d in debts_in or []:
        out.append(Debt(
            name=str(d.get("name", "Debt")),
            balance=float(d.get("balance", 0.0)),
            apr=float(d.get("apr", 0.0)),
            min_payment=float(d.get("min_payment", 0.0)),
        ))
    return out

def payoff_plan(debts_in: List[Dict[str, Any]], method: str = "avalanche") -> Dict[str, Any]:
    """
    Return a simple plan with next focus account and recommended extra payment.
    method: 'avalanche' (highest APR first) or 'snowball' (smallest balance first)
    """
    debts = _normalize_debts(debts_in)
    if not debts:
        return {"next_focus": None, "recommendation": "No debts found.", "schedule": []}

    if method == "snowball":
        debts.sort(key=lambda d: (d.balance, -d.apr))
    else:
        method = "avalanche"
        debts.sort(key=lambda d: (-d.apr, d.balance))

    focus = debts[0]
    total_min = sum(d.min_payment for d in debts)
    # Heuristic: propose 10% of income as total debt budget if feasible
    recommended_total = max(total_min, 0.10 *  float(getattr(focus, "balance", 0)) / 12.0)
    # If state has income, bias up to 15% of income
    extra_hint = None
    focus_extra = 0.0

    # Try to pull income if available (not mandatory)
    try:
        income = float(getattr(__import__("builtins"), "STATE_INCOME_PROXY", 0.0))  # placeholder
    except Exception:
        income = 0.0

    # If the app sets a proxy or passes income later we can improve this.
    if income > 0:
        recommended_total = max(recommended_total, 0.12 * income)

    focus_extra = max(0.0, recommended_total - total_min)
    extra_hint = f"Pay minimums on all, then add {inr(focus_extra)} extra to **{focus.name}**."

    schedule = [
        {"debt": d.name, "strategy": "min" if d is not focus else "min+extra",
         "amount": d.min_payment + (focus_extra if d is focus else 0.0)}
        for d in debts
    ]

    return {
        "method": method,
        "next_focus": focus.name,
        "recommended_total_payment": round(sum(item["amount"] for item in schedule), 2),
        "recommendation": extra_hint,
        "schedule": schedule,
    }

# ---- Overspend alerts ----
def detect_overspend_alerts(state) -> List[Dict[str, Any]]:
    """
    Compare (rough) category spend vs soft limits as % of income.
    This stub uses state.monthly_spend and default limits to produce friendly nudges.
    Replace with real category aggregation once transactions are wired.
    """
    income = float(getattr(state, "income", 0.0))
    if income <= 0:
        return []

    monthly_spend = float(getattr(state, "monthly_spend", 0.0))
    # Naive category split for now; later replace with actual category sums from DB.
    est_split = {
        "groceries": monthly_spend * 0.20,
        "dining": monthly_spend * 0.12,
        "shopping": monthly_spend * 0.10,
        "transport": monthly_spend * 0.08,
        "entertainment": monthly_spend * 0.06,
    }

    alerts: List[Dict[str, Any]] = []
    for cat, spent in est_split.items():
        limit_ratio = DEFAULT_CATEGORY_LIMITS.get(cat, 0.07)
        soft_cap = income * limit_ratio * 1.10  # 10% grace
        if spent > soft_cap:
            alerts.append({
                "category": cat,
                "spent": round(spent, 2),
                "soft_cap": round(soft_cap, 2),
                "message": f"{cat.capitalize()} spend {inr(spent)} is above your soft cap {inr(soft_cap)}. Try 10% less next month.",
            })
    return alerts

# ---- Simple rules engine hooks (placeholders for future policy/guardrails) ----
def load_policy() -> Dict[str, Any]:
    """
    In production, read JSON/YAML from configs/policy/.
    Here we return the in-module defaults so the app runs out-of-the-box.
    """
    return {
        "budget_rule": DEFAULT_BUDGET_RULE,
        "category_limits": DEFAULT_CATEGORY_LIMITS,
        "advice_language": "simple",
        "guardrails": {
            "no_investment_advice": True,
            "no_tax_advice": True,
        },
    }
    # ---- Goal helpers ----
def suggest_starter_goals(state) -> List[Dict[str, Any]]:
    """
    Create a sensible first set of goals based on income and debts.
    """
    monthly_income = float(getattr(state, "income", 60000.0) or 0)
    emergency_target = max(50000.0, round(monthly_income * 3, -3))  # ~3 months buffer, rounded

    goals = [
        {"name": "Emergency Fund", "target": emergency_target, "deadline": "2026-03-31", "saved": 0},
    ]

    # If debts exist, add a "Debt Cushion" subgoal to front-load extra payment buffer
    if getattr(state, "debts", []):
        goals.append({"name": "Debt Cushion", "target": min(30000.0, emergency_target * 0.4),
                      "deadline": "2025-12-31", "saved": 0})
    return goals


def update_goal_progress(state) -> List[Dict[str, Any]]:
    """
    Very simple progress update: if an autosave suggestion exists, apply part of it;
    otherwise estimate progress from savings_rate * income.
    """
    goals = list(getattr(state, "goals", []))
    if not goals:
        return goals

    monthly_income = float(getattr(state, "income", 0.0) or 0.0)
    autosave = float(getattr(state, "suggested_autosave", 0.0) or 0.0)
    # Apply 1/4 of autosave to first active goal as a demo effect
    monthly_contribution = autosave * 0.25 if autosave > 0 else monthly_income * float(getattr(state, "savings_rate", 0.15))

    for g in goals:
        if g.get("target"):
            g["saved"] = float(g.get("saved", 0.0)) + monthly_contribution * 0.3  # conservative portion
            # clamp
            g["saved"] = min(g["saved"], float(g["target"]))
    return goals


# ---- Advice generator (placeholder) ----
def generate_advice(state) -> str:
    """
    Non-LLM placeholder that speaks like a friendly coach.
    """
    income = float(getattr(state, "income", 0.0))
    savings_rate = float(getattr(state, "savings_rate", 0.15))
    budget = getattr(state, "budget", {}) or {}
    savings_amt = budget.get("savings", income * savings_rate)

    tips = []
    if savings_rate < 0.10:
        tips.append("try nudging your savings rate up by 1–2% this month")
    if float(getattr(state, "monthly_spend", 0.0)) > income * 0.9:
        tips.append("trim one discretionary category by ~10%")
    if getattr(state, "debts", []):
        tips.append("keep extra payments focused on the current target account")

    suffix = (" Tip: " + "; ".join(tips) + ".") if tips else ""
    return f"You're doing well. Keep an automatic transfer of {inr(savings_amt)} on the 1st, review subscriptions quarterly, and stay consistent.{suffix}"


# ---- Debt payoff planning (upgraded to match your agent expectations) ----
def payoff_plan(debts_in: List[Dict[str, Any]], method: str = "avalanche") -> Dict[str, Any]:
    """
    Return a plan with:
      - method: str
      - next_focus: {name, extra_payment}
      - order: [{name, balance, apr, months_est}]
      - projected_interest_saved: float (very rough heuristic)
      - recommended_total_payment: float
      - schedule: [{debt, strategy, amount}]
    """
    debts = _normalize_debts(debts_in)
    if not debts:
        return {
            "method": method,
            "next_focus": {"name": None, "extra_payment": 0.0},
            "order": [],
            "projected_interest_saved": 0.0,
            "recommended_total_payment": 0.0,
            "schedule": [],
            "recommendation": "No debts found."
        }

    # Order debts
    if method == "snowball":
        debts.sort(key=lambda d: (d.balance, -d.apr))
    else:
        method = "avalanche"
        debts.sort(key=lambda d: (-d.apr, d.balance))

    focus = debts[0]
    total_min = sum(d.min_payment for d in debts)

    # Heuristic monthly total to aim for
    # If income is available on state, you can pass it via a global or adjust here later.
    recommended_total = max(total_min, focus.balance * 0.10 / 12.0)
    focus_extra = max(0.0, recommended_total - total_min)

    # Simple schedule
    schedule = [
        {"debt": d.name, "strategy": "min" if d is not focus else "min+extra",
         "amount": round(d.min_payment + (focus_extra if d is focus else 0.0), 2)}
        for d in debts
    ]

    # Very rough interest saved estimate vs paying only minimums for a year
    mean_apr = sum(d.apr for d in debts) / len(debts)
    projected_interest_saved = round(focus_extra * 12 * mean_apr * 0.5, 2)  # tiny heuristic

    # naive months estimate per debt
    order = []
    for d in debts:
        monthly = d.min_payment + (focus_extra if d is focus else 0.0)
        months_est = int(max(1, round(d.balance / max(monthly, 1.0))))
        order.append({"name": d.name, "balance": d.balance, "apr": d.apr, "months_est": months_est})

    plan = {
        "method": method,
        "next_focus": {"name": focus.name, "extra_payment": round(focus_extra, 2)},
        "order": order,
        "projected_interest_saved": projected_interest_saved,
        "recommended_total_payment": round(sum(item["amount"] for item in schedule), 2),
        "schedule": schedule,
        "recommendation": f"Pay minimums on all, then add {inr(focus_extra)} to **{focus.name}**."
    }
    return plan

