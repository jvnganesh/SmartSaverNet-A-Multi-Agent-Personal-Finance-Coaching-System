# configs/__init__.py
from pathlib import Path
import yaml

CONFIG_ROOT = Path(__file__).resolve().parent

def load_yaml(relpath: str) -> dict:
    with open(CONFIG_ROOT / relpath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_prompt(name: str) -> str:
    p = CONFIG_ROOT / "prompts" / f"{name}.md"
    return p.read_text(encoding="utf-8")

# add at bottom
from .policy.schema import PolicyCfg

def load_policy() -> PolicyCfg:
    raw = load_yaml("policy/thresholds.yaml")
    return PolicyCfg(**raw)
