# Demo script — 4 minutes

For the Round-2 live demo (or the recorded walkthrough). Times are targets, not rules.

## Before you start

- [ ] Open the dashboard, `/work-orders`, `/models`, `/about` in four tabs.
- [ ] Hit `/api/health` once to wake the free API (first call after sleep: ~45 s).
- [ ] Confirm the fleet tab shows **100** machines and **API online**.
- [ ] Have the retrain tab ready — it takes ~2–5 s locally, ~30 s on the free host.

If the API is asleep during judging, say it plainly: "free instance, warming up" —
then show `/api/health` returning `ok`. Do not pretend it is instant.

---

## Scene 1 — The problem (30 s) · Fleet tab

> "A connected fleet streams vibration, temperature and pressure every cycle. Today
> you find out when it breaks. We score the whole fleet continuously, so a machine
> tells you it is dying before it stops."

Point at the KPI row: **100 machines, 14 critical, average 78 cycles of life left,
24 open work orders.**

> "Severity is not a black box: every chip has a reason attached. That reason is on
> the work order."

---

## Scene 2 — Why this machine? (45 s) · click a CRITICAL engine

> "This is engine 42. The model says 25 cycles left; the true label is 10 — so it is
> optimistic, which is the error direction we punish in the PHM score."

Point at the chart:

> "Green falls as life is consumed. Amber is the anomaly percentile from an
> IsolationForest trained only on healthy early life — it climbs before the RUL
> collapses. Two independent signals agreeing is what makes a CRITICAL call."

Scroll to the audit trail:

> "Every agent decision is logged with the exact threshold that fired. A judge can
> ask 'why?' and the answer is already on screen."

---

## Scene 3 — Humans only see exceptions (45 s) · Work orders tab

> "CRITICAL and HIGH open a work order automatically. MEDIUM goes to this human
> queue. LOW is logged and never bothers anyone."

Click **Resolve** on a MEDIUM order, add nothing:

> "That is the whole human workload: approve or dismiss. The agent does not re-open
> a settled machine unless it gets genuinely worse — so the queue does not thrash."

Switch to **Settled** to show the action landed.

---

## Scene 4 — The closed loop (60 s) · Models & monitoring tab

> "Two models compete on identical features. Ridge is the explainable baseline;
> gradient boosting wins on validation RMSE, 17.6 versus 21.0."

Press **Retrain & re-score fleet**:

> "This runs the real pipeline — features, fit, validate, promote, re-score, rebuild
> the work-order queue. No simulated numbers."

While it runs, point at the run table:

> "Metrics are mirrored into SQLite because MLflow history can be wiped on a
> redeploy. The history survives."

When it finishes:

> "New version promoted, new test metrics, and the fleet ranking may change. That is
> the loop closing: data in, model out, decisions updated."

---

## Scene 5 — Honesty (30 s) · About tab

> "Simulated benchmark engines, not a real asset. RUL is capped at 125 cycles. The
> free host has an ephemeral disk. And there is no LLM anywhere in this path — the
> agent is thresholds you can audit."

> "What is real: the data pipeline, the leakage-safe split, the metrics, the API,
> the dashboard, the retrain loop. Every number on screen comes from the committed
> pipeline."

---

## Likely questions

**Why not an LLM?**
The brief forbids it, and thresholds are auditable. An LLM would add latency, cost
and non-determinism without improving a three-signal decision.

**Where is the leakage control?**
Split is by engine, never by row; the test features are stored without labels, and
ground truth is a separate file. `tests/test_dataset.py` proves it.

**Why is the model optimistic on engine 42?**
RUL regression compresses toward the mean, and the cap at 125 truncates the tail.
PHM scoring makes late predictions expensive, which is why critical recall matters
more than raw accuracy here.

**How do you handle rare failures?**
Critical recall is a first-class metric (0.90 on test) and the agent's CRITICAL band
is derived from the same 15-cycle threshold — model and rules cannot drift apart.

**What breaks at scale?**
SQLite and a single process. The next step is Postgres plus a queue for retraining;
the API is already a thin layer over the store, so that swap is contained.
