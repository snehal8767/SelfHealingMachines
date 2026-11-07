# Deploying Self-Healing Machines

Target architecture (same shape as your CitrusGuardAI deployment):

| Piece | Host | Result |
|---|---|---|
| React dashboard | Vercel | `https://<project>.vercel.app` |
| FastAPI + SQLite | Render (free) | `https://<service>.onrender.com` |

Everything below is prepared in this repo: `frontend/vercel.json`, `render.yaml`,
`backend/requirements.txt`, seeded `data/shm.db`, committed FD001 raw data and models.

---

## 0. What you need

- A GitHub account (this repo has no remote yet).
- Vercel account (you already have one — CitrusGuardAI is there).
- Render account (you already have one — CitrusGuardAI's API is there).
- VS Code with the Python and Tailwind extensions (see `.vscode/extensions.json`).

---

## 1. Open the project in VS Code

From `C:\Users\snehal\OneDrive\Desktop\SelfHealingMachines`:

```powershell
code .
```

Recommended tasks are in `.vscode/tasks.json` (Ctrl+Shift+B opens the list):

- **API: start** → uvicorn on port 8000
- **Dashboard: dev** → Vite on port 5173
- **Tests: python** → pytest
- **Frontend: build** → type-check + production build

Interpreter: `.venv\Scripts\python.exe` (already set in `.vscode/settings.json`).

---

## 2. Push to GitHub

### 2a. Create the empty repository

On github.com → **New repository** → name `SelfHealingMachines` → **Private or Public**
→ do **not** add README/.gitignore → **Create**.

### 2b. Push

```powershell
git add -A
git commit -m "Full prototype: pipeline, API, dashboard, deployment config"
git remote add origin https://github.com/snehal8767/SelfHealingMachines.git
git push -u origin main
```

If `origin` already exists: `git remote set-url origin https://github.com/snehal8767/SelfHealingMachines.git`.

> The repo intentionally contains ~11 MB of benchmark data and fitted models.
> They are required so the free API can serve predictions and retrain without a
> training step at boot. Processed parquet files are excluded.

---

## 3. Deploy the API on Render

1. Render dashboard → **New +** → **Blueprint**.
2. Connect GitHub → pick `SelfHealingMachines` → **Apply**.
3. Render reads `render.yaml` and creates `self-healing-machines-api`.
4. Wait for the first build (3–6 minutes: pip install of pandas/sklearn).
5. Open `https://<service>.onrender.com/api/health`. Expected:

```json
{"status":"ok","subset":"FD001","db_ready":true,"engines":100}
```

If it returns `degraded`, check the Logs tab — the committed `data/shm.db` is the
seed, and `SHM_DB_PATH=data/shm.db` is set by the blueprint.

**Note:** free instances sleep after ~15 minutes. The first request after a sleep
takes ~30–60 s. That is normal.

### Required: enable owner writes

The dashboard is public to read, but **only the owner can change data**. Writes
fail closed until a key exists:

1. Generate a key locally:

   ```powershell
   [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }))
   ```

2. Render → service → **Environment** → add `SHM_API_TOKEN` = that value →
   save (the service redeploys).
3. Open the dashboard → **Owner access** (top bar) → paste the key → **Unlock**.
   It is checked by the server and stored only in that browser.

Do **not** create `VITE_API_TOKEN` in Vercel. Vite bakes it into public
JavaScript, which would hand every visitor the key.

Verify the closed loop is protected:

```bash
curl -X POST https://<service>.onrender.com/api/retrain -H "Content-Type: application/json" -d "{}"
# => 401 {"detail":"Invalid or missing X-API-Token"}
```

---

## 4. Deploy the dashboard on Vercel

1. Vercel dashboard → **Add New…** → **Project** → import `SelfHealingMachines`.
2. **Root Directory** → `frontend` (important — do not deploy the repo root).
3. Framework preset: **Vite** (auto-detected). Build `npm run build`, output `dist`.
4. **Environment Variables** → add:

   | Name | Value |
   |---|---|
   | `VITE_API_URL` | `https://<service>.onrender.com` |

5. **Deploy**.
6. Open the deployment URL and check all five screens.

`VITE_API_URL` is baked in at build time. If you change it, redeploy **without**
the build cache (Deployments → ⋯ → Redeploy → uncheck "Use existing Build Cache").

### CLI alternative

```powershell
npm install -g vercel
cd frontend
vercel login
vercel --prod
# when prompted: link to a new project, framework Vite, build `npm run build`, output `dist`
```

Add `VITE_API_URL` first with `vercel env add VITE_API_URL production`.

---

## 5. Verification checklist

- [ ] `GET /api/health` → `"status":"ok"`, `"engines":100`
- [ ] `GET /api/fleet` → 100 engines, 14 CRITICAL / 10 HIGH / 18 MEDIUM / 58 LOW
- [ ] `/` shows 100 rows and "API online"
- [ ] `/work-orders` shows 42 orders; Resolve changes a card to Settled
- [ ] `/models` shows test RMSE 18.7 and the run history
- [ ] Retrain button → status QUEUED → RUNNING → DONE, run table gains a row
- [ ] `/about` renders dataset provenance and limitations
- [ ] Browser console has no errors

---

## 6. Redeploy after a change

```powershell
git add -A
git commit -m "describe the change"
git push
```

- **Vercel:** auto-deploys on push (Git integration).
- **Render:** auto-deploy is on by default for Blueprint services; otherwise
  **Manual Deploy → Deploy latest commit**.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Dashboard shows "API offline" | `VITE_API_URL` missing or wrong | Set it in Vercel, redeploy without cache |
| `Cannot reach the API at http://localhost:8000` on the live site | The build used the default URL | Same fix as above |
| CORS error in console | `SHM_CORS_ORIGINS` restricted | Blueprint sets `*`; if you changed it, include the Vercel domain |
| Health returns `degraded` | DB missing/unreadable | Confirm `data/shm.db` is in the repo and `SHM_DB_PATH` is correct |
| Resolve returns 401 | Wrong or missing owner key | Click **Owner access** and unlock with the same value as `SHM_API_TOKEN` |
| Resolve/retrain returns 503 | `SHM_API_TOKEN` not set on the server | Add it in Render → Environment (writes fail closed by design) |
| Retrain returns 503 | Raw FD001 files missing on the host | Ensure `data/raw/cmapss/data/*_FD001.txt` are committed |
| Retrain stuck on RUNNING | Render instance restarted mid-job | Jobs are in-memory; retry once the service is awake |
| `dist` not found on Vercel | Root directory not set to `frontend` | Project settings → Root Directory → `frontend` |

---

## Cost

Both hosts are on free tiers. No paid add-ons, no external LLM calls, no database
service — SQLite ships as a file inside the repo.
