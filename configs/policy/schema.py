# configs/policy/schema.py
from pydantic import BaseModel, Field, conint, confloat
from typing import Optional

class SavingsCfg(BaseModel):
    min_savings_rate: confloat(ge=0, le=1) = 0.10
    max_auto_transfer_rate: confloat(ge=0, le=1) = 0.30

class DebtCfg(BaseModel):
    avalanche_default: bool = True
    min_payment_floor: conint(ge=0) = 1000

class AlertsCfg(BaseModel):
    overspend_trigger_pct_of_budget: confloat(ge=0, le=1) = 0.85
    high_single_txn_multiple_of_mean: confloat(gt=0) = 4.0

class RiskCfg(BaseModel):
    max_single_recommendation_amount: conint(ge=0) = 20000

class UiCfg(BaseModel):
    default_currency: str = "INR"
    date_format: str = "YYYY-MM-DD"

class PolicyCfg(BaseModel):
    version: int = 1
    savings: SavingsCfg = SavingsCfg()
    debt: DebtCfg = DebtCfg()
    alerts: AlertsCfg = AlertsCfg()
    risk: RiskCfg = RiskCfg()
    ui: UiCfg = UiCfg()
