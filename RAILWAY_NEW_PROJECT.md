# New Railway project + GitHub (LiveContactBot)

**Current CLI project (2026-09-10):** `LiveContactBot`  
**Public URL:** https://contactbot-production-17b3.up.railway.app  
**Project ID:** `b656f5dc-cd3e-4de1-96fc-a369c3584688`

Repo: **https://github.com/ShashwatKumar01/LiveContactBot.git**  
Branch: **main** (already contains latest ContactBot code)

### Free plan note (Redis)

Railway **free** tier allows only **2 services** (here: `contactbot` + `MongoDB`). Adding **Redis** on Railway failed with *resource provision limit*. Use one of:

1. **Upgrade** Railway plan → `railway add -d redis --json --verbose true` → set `REDIS_URL=${{Redis.REDIS_URL}}` on `contactbot`.
2. **Upstash Redis** (free): create DB → `railway variable set REDIS_URL=rediss://... --service contactbot`
3. **MongoDB Atlas** instead of Railway Mongo → delete Railway MongoDB service → add Railway Redis (still 2 services).

## 1. Push code (local)

```powershell
cd d:\python\Telegrambots\ContactBot
git remote -v
# should show origin → ShashwatKumar01/LiveContactBot.git
git push origin main
```

## 2. Railway project

1. [railway.app](https://railway.app) → **New Project**.
2. **Deploy from GitHub repo** → select **ShashwatKumar01/LiveContactBot** (install [Railway GitHub App](https://github.com/apps/railway-app) if asked).
3. Branch: **main**. Root directory: **/** (repo root = ContactBot app).
4. In the same project, click **+ New** → **Database** → **MongoDB** and **Redis** (or add from templates).

## 3. ContactBot service variables

Open your **app service** (not Mongo/Redis) → **Variables**. Use **Raw Editor** and paste (replace secrets):

```env
MASTER_BOT_TOKEN=your_master_bot_token_from_botfather
MONGODB_URI=${{MongoDB.MONGO_URL}}
MONGODB_DATABASE=contactbot
REDIS_URL=${{Redis.REDIS_URL}}
ENVIRONMENT=production
WEBHOOK_PATH=/webhook/master
WEBHOOK_SECRET=generate_a_long_random_string_here
SUPER_ADMIN_IDS=your_telegram_user_id
ADMIN_WEB_PASSWORD=choose_a_strong_password
ADMIN_WEB_SECRET=another_long_random_string
TOKEN_ENCRYPTION_KEY=optional_fernet_key_or_leave_empty_for_dev_only
SKIP_DB_INDEXES=true
```

**After first deploy:** **Settings** → **Networking** → **Generate domain** → copy `https://xxxx.up.railway.app` → add:

```env
WEBHOOK_HOST=https://xxxx.up.railway.app
```

(No trailing slash on `WEBHOOK_HOST`.)

Redeploy once after setting `WEBHOOK_HOST`.

> `${{MongoDB.MONGO_URL}}` and `${{Redis.REDIS_URL}}` must match the **service names** in your project. In Variables, use **Add Reference** and pick MongoDB / Redis if names differ.

## 4. Mongo disk (Railway Mongo only)

If the app crashes with Mongo error **14031** / out of disk: resize Mongo volume to **1 GB+** (Hobby) or use **[DEPLOY_ATLAS.md](DEPLOY_ATLAS.md)** and set `MONGODB_URI` to Atlas. Remove `SKIP_DB_INDEXES` when disk/indexes are healthy.

## 5. Verify

```text
https://YOUR-DOMAIN.up.railway.app/health
https://YOUR-DOMAIN.up.railway.app/admin
```

Telegram: master bot `/start`, `/addbot`.

## 6. Auto-deploy

With GitHub connected, every `git push origin main` redeploys automatically.

### CLI (optional)

```powershell
railway login
cd d:\python\Telegrambots\ContactBot
railway link
railway up
```

Or connect repo:

```powershell
railway service
railway service source connect --repo ShashwatKumar01/LiveContactBot --branch main
```
