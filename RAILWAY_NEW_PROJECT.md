# Railway layout (recommended)

**Project:** `LiveContactBot`  
**Public URL:** https://contactbot-production-17b3.up.railway.app

## Services (2 only)

| Service | Role |
|---------|------|
| **contactbot** | App (Dockerfile / `contact.py`) |
| **Redis** | FSM state + child-bot storage (**required**) |

**Do not** add Railway MongoDB — use **MongoDB Atlas** on the app service:

```env
MONGODB_URI=mongodb+srv://USER:PASS@cluster....mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=ChatReplyBot
REDIS_URL=${{Redis.REDIS_URL}}
```

## CLI setup

```powershell
cd d:\python\Telegrambots\ContactBot
railway init --name LiveContactBot
railway add --service contactbot
railway add -d redis --json --verbose true
railway service delete -s MongoDB -y   # if an old Mongo plugin exists
railway service link contactbot
railway variable set 'REDIS_URL=${{Redis.REDIS_URL}}' --service contactbot
# Set MONGODB_URI, MONGODB_DATABASE, MASTER_BOT_TOKEN, WEBHOOK_*, etc.
railway domain --service contactbot
railway variable set WEBHOOK_HOST=https://YOUR-DOMAIN.up.railway.app --service contactbot
railway up --service contactbot --detach
```

## GitHub auto-deploy

Connect repo `ShashwatKumar01/LiveContactBot` branch `main` in Railway dashboard (GitHub App access required).

See also [DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md), [DEPLOY_ATLAS.md](DEPLOY_ATLAS.md), [BACKUP_MONGODB.md](BACKUP_MONGODB.md).
