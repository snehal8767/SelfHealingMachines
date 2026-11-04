# DEPLOYMENT_PLAN.md

Status: `NOT STARTED` — Phase 10

Reuse of the **proven CitrusGuardAI pipeline** (Vercel + Render), so deployment is a known path.

---

## Target architecture

| Piece | Platform | Notes |
|---|---|---|
| React dashboard | **Vercel** | static build; `/api` proxied to backend via `vercel.json` |
| FastAPI + ML pipeline | **Render** (free web service) | serves API + model artifact; auto-bootstraps DB/seed at startup |
| Database | **SQLite** on Render disk (ephemeral) | demo data re-seeds at boot — acceptable for hackathon PoC |
| Experiment tracking | **MLflow local file store** on Render | `mlruns/` regenerates; keep a committed `runs_summary.json` snapshot so the monitoring page always shows history |

> **Honest limitation to disclose:** on the free tier the filesystem is ephemeral, so MLflow
> history resets on redeploy. Mitigation: export metrics to SQLite `model_runs` on every train.

## Environment variables (names only — never commit values)

| Name | Where | Purpose |
|---|---|---|
| `DATABASE_URL` | Render | SQLite path |
| `API_TOKEN` | Render + Vercel | guards `/retrain` and `/work-orders/{id}/resolve` |
| `VITE_API_URL` | Vercel (Config type, **not** Secret) | direct API base; falls back to `/api` proxy |
| `CORS_ORIGINS` | Render | deployed frontend origin |
| `MLFLOW_TRACKING_URI` | Render | `file:./mlruns` |

⚠️ Lessons already learned on CitrusGuardAI:
- Vercel env vars are baked **at build time** → redeploy **without build cache** after changing them
- Never mark a `VITE_` variable as *Secret* — it will not reach the browser bundle

## Deployment steps

1. **Backend → Render**
   - Create Web Service from the GitHub repo, root = `backend/`
   - Start command runs migrations/seed → `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add env vars from the table → **Manual Deploy → Deploy latest commit**
2. **Frontend → Vercel**
   - Import repo, root = `frontend/`, framework = Vite
   - Add `VITE_API_URL` (type **Config**) or rely on the `/api` proxy rewrite
   - Deploy, then **redeploy without cache** if env vars changed
3. **Verify (never claim success without this)**
   - `GET <backend>/health` → JSON with `status: ok`
   - Open live site → login/dashboard loads with **real** API data
   - Check Render **Logs** for startup/bootstrap lines and errors
   - Run one full journey: fleet → engine detail → work order → resolve → retrain

## Rollback
- Vercel: Deployments → previous Ready deployment → Promote
- Render: previous deploy → Rollback

## Pre-deployment checklist
- [ ] `pytest` green locally
- [ ] production build succeeds (`npm run build`)
- [ ] no secrets in git (`git grep -i "api_key\|secret\|password"` spot-check)
- [ ] `.env.example` committed instead of `.env`
- [ ] README with run instructions
