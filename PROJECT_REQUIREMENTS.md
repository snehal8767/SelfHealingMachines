# PROJECT_REQUIREMENTS.md

**TELIPORT Season 4 (Tata Elxsi) — Case Study 1**
**Self-Healing Machines: Predictive Maintenance for a Connected Fleet**

Status: `IN PROGRESS` · Phase 1 — Requirement Analysis

---

## 1. Problem statement

A fleet of connected machines (trucks, buses, industrial compressors) continuously streams
sensor data: **vibration, temperature, motor current, pressure, RPM**.

Today failures are caught **after a breakdown** or on **fixed service intervals**, causing
unplanned downtime and higher maintenance cost.

**Build a closed-loop system** that:

1. ingests the sensor data,
2. detects early signs of degradation,
3. predicts how much useful life a machine has left (RUL),
4. **automatically raises a maintenance work order**,
5. with a **human stepping in only for exceptions**.

## 2. Hard constraints (ground rules)

| # | Rule | Implication |
|---|---|---|
| G1 | Failures rarer than normal readings — handle **mild imbalance** | Report recall/precision on failures, not just RMSE; choose thresholds deliberately |
| G2 | Pipeline runs **end-to-end without manual steps** once data is provided | One command / one click runs: clean → features → train → predict → triage → work order |
| G3 | **No LLM.** Agent = simple rules or thresholds | Plain Python rule engine only |
| G4 | Open-source tools; design **documented clearly** for review | Every choice must be explainable in the deck |

## 3. Dataset (official, NASA)

**NASA C-MAPSS Turbofan Engine Degradation** — run-to-failure sensor readings,
**21 sensors + 3 operating settings**, true **RUL** labels for evaluation.

- Four subsets, increasing difficulty: **FD001 → FD004**
- Default plan: **FD001 first** (simplest, fastest to a working PoC), then extend if time allows
- Source: `data.nasa.gov/dataset/cmapss-jet-engine-simulated-data`

## 4. The four required layers

| Layer | What must be built |
|---|---|
| **Data Engineering** | Read sensor data (batch or streaming), clean (missing values, basic noise), build **rolling-window features** (averages, trends) |
| **Machine Learning** | Detect abnormal behaviour **and** predict **Remaining Useful Life (RUL)** |
| **MLOps** | Track experiments + model versions, show a **retraining flow** when new data arrives, plus a basic **monitoring view** |
| **Agent (non-LLM)** | Rule-based **Triage Agent**: reads model output → decides severity → **auto-creates a maintenance work order** |

## 5. Deliverables

### Round 1 — Design deck (Idea Submission)
- Architecture diagram: `data → features → model → agent → work order`
- Approach for cleaning data and building features
- Choice of anomaly-detection and RUL models **with reasoning**
- Logic the Triage Agent will use

### Round 2 — Proof of Concept (14 Nov 2026 10:00 → 13 Dec 2026 23:59 IST)
- Working pipeline on the chosen C-MAPSS subset(s)
- Trained model with RUL predictions
- A simple monitoring dashboard
- Agent auto-generating a work order **+ a demo retraining run**

## 6. Judging criteria (weights)

### Round 1 — evaluation of design
| Criterion | Weight |
|---|---|
| Problem understanding | 15% |
| Architecture clarity | **20%** |
| Data engineering approach | 15% |
| ML approach & reasoning | **20%** |
| MLOps & agent logic | 15% |
| Dataset coverage | 10% |
| Communication quality | 5% |

### Round 2 — evaluation of proof of concept
| Criterion | Weight |
|---|---|
| Working pipeline | **20%** |
| Data engineering quality | 15% |
| Model performance | 15% |
| MLOps in action | 10% |
| Agent behavior | 10% |
| Dataset coverage | 10% |
| Demo & explanation | **20%** |

## 7. Submission rules
- Formats: `.ppt` / `.pptx` / `.pdf`, **< 5 MB**
- Naming: `Leader's First Name_Team Name_Institute Name`
- **Only the team leader** can submit (changeable until deadline)
- Supporting sheets go in annexures

## 8. Explicitly out of scope (v1)
- Any LLM / generative-AI feature (forbidden by G3)
- Real physical IoT hardware (stream is simulated from the dataset)
- Multi-tenant production auth/billing

## 9. Open questions
See `IMPLEMENTATION_PLAN.md` §Open Questions — the blocking ones are:
Round-1 submission status, subset choice, and dashboard technology.
