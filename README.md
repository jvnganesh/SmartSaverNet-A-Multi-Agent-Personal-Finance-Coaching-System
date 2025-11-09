# SmartSaverNet 💸 — Multi-Agent Personal Finance Coaching System

SmartSaverNet is an **AI-driven personal finance assistant** where **multiple specialized agents** work together to help users:

- Build and maintain a practical **monthly budget**
- Grow savings through **low-friction micro-saving strategies**
- Pay down debt using **avalanche / snowball** payoff methods
- Track and progress meaningful **financial goals**
- Receive **spending alerts** before overspending happens
- Get **friendly, understandable financial advice**

This project demonstrates **coordinated multi-agent reasoning**, a shared **state container**, and an optional **transaction analytics pipeline**.

---

## 🚀 Features

| Agent | Role | Outcome |
|------|------|---------|
| **Budget Agent** | Computes monthly budget plan | Essentials / Wants / Savings allocation |
| **Savings Agent** | Identifies micro-savings opportunities | Autosave suggestion + saving tips |
| **Debt Agent** | Generates fastest payoff strategy | Ordered repayment schedule |
| **Goal Agent** | Creates and updates progress on goals | Milestones + projected completion |
| **Spending Alert Agent** | Detects overspending by category | Gentle advisory nudges |
| **Advice Agent** | Summarizes strategy in simple language | Friendly coaching messages |

All agents share and update a central **UserState**.

---

## 🧱 System Architecture

smartsavernet/
│
├── app.py # Streamlit UI
│
├── agents/ # Individual agent modules
│ ├── budget.py
│ ├── savings.py
│ ├── debt.py
│ ├── goals.py
│ ├── alerts.py
│ └── advice.py
│
├── orchestrator/ # Multi-agent coordination
│ ├── state.py # Unified UserState model
│ ├── graph.py # Agent pipeline via LangGraph
│ └── tools.py # Calculation + logic helpers
│
├── data/ # Optional storage layer
│ ├── db.py # SQLite utilities
│ └── seed_mock.py # Synthetic transaction generator
│
└── configs/ # Prompt & policy configuration (future use)
├── prompts/
└── policy/



---

## 🖥️ UI Preview

- Built in **Streamlit**
- Enable / disable agents dynamically
- Run agents once per click
- View live **messages**, **budget**, **goals**, and **transactions**

---

## 🔧 Setup Instructions

### 1) Clone
```bash
git clone https://github.com/<your-username>/SmartSaverNet.git
cd SmartSaverNet

2) Create & activate virtual environment

Windows

python -m venv .venv
.venv\Scripts\activate


Mac/Linux

python3 -m venv .venv
source .venv/bin/activate

3) Install dependencies
pip install -r requirements.txt

4) Launch the app
streamlit run app.py
```



