# Deploy ContactBot on Railway

**New Railway project?** Step-by-step: **[RAILWAY_NEW_PROJECT.md](RAILWAY_NEW_PROJECT.md)**  
GitHub repo: https://github.com/ShashwatKumar01/LiveContactBot.git

## 1. Create project and services

1. In [ContactBot](.) directory: `railway login` (if needed), then `railway init`.
2. In Railway dashboard, add **MongoDB** and **Redis** to the same project.
3. **MongoDB disk (required if using Railway Mongo):** The Railway Mongo template uses a **500 MB** volume; MongoDB needs **≥ 512 MB free**, which causes `OutOfDiskSpace` / `code 14031`.  
   - **Trial plan:** You cannot grow the volume — use **[DEPLOY_ATLAS.md](DEPLOY_ATLAS.md)** (MongoDB Atlas M0 free) instead.  
   - **Hobby plan+:** MongoDB service → click **mongodb-volume** → **Settings** → **Live Resize** → **1024 MB** or more ([Railway docs](https://docs.railway.com/volumes)).
3. On the **ContactBot** service, set variables (see below). Reference plugin URLs, e.g. `${{MongoDB.MONGO_URL}}` — use the exact names Railway shows for your plugins.

## 2. Required variables (ContactBot service)

| Variable | Value |
|----------|--------|
| `MASTER_BOT_TOKEN` | From @BotFather |
| `MONGODB_URI` | Atlas `mongodb+srv://...` (recommended) or Railway `${{MongoDB.MONGO_URL}}` |
| `MONGODB_DATABASE` | `ChatReplyBot` |
| `REDIS_URL` | From Redis service |
| `ENVIRONMENT` | `production` |
| `WEBHOOK_HOST` | `https://YOUR-SERVICE.up.railway.app` (no trailing slash) |
| `WEBHOOK_PATH` | `/webhook/master` |
| `WEBHOOK_SECRET` | Long random string |
| `SUPER_ADMIN_IDS` | Your Telegram user ID |
| `ADMIN_WEB_PASSWORD` | Web `/admin` login |
| `ADMIN_WEB_SECRET` | Session signing secret |
| `TOKEN_ENCRYPTION_KEY` | Optional Fernet key |

Railway sets `PORT` automatically; the app uses it for `APP_PORT`.

## 3. Public URL and webhooks

1. Enable **Public Networking** on the ContactBot service.
2. Copy the HTTPS domain → set `WEBHOOK_HOST`.
3. Redeploy so Telegram master + child webhooks use the correct URL.

## 4. Deploy

```bash
cd ContactBot
railway up
```

### GitHub (recommended)

Repo: [github.com/ShashwatKumar01/LiveContactBot](https://github.com/ShashwatKumar01/LiveContactBot)

1. Install the [Railway GitHub App](https://github.com/apps/railway-app) and grant access to **LiveContactBot**.
2. Railway dashboard → **contactbot** service → **Settings** → **Connect Repo** → `ShashwatKumar01/LiveContactBot`, branch **main**.
3. Or CLI (after GitHub access is granted):
   ```bash
   railway service source connect --repo ShashwatKumar01/LiveContactBot --branch main --service contactbot
   ```

Pushes to `main` will auto-deploy.

## 5. Verify

- `curl https://YOUR-SERVICE.up.railway.app/health`
- `https://YOUR-SERVICE.up.railway.app/admin`
- Master bot: `/start`, `/addbot`

Do **not** commit `.env` (see `.gitignore`).

## Backups

Regular Mongo exports: **[BACKUP_MONGODB.md](BACKUP_MONGODB.md)** and `scripts/backup-mongo.ps1`. Also save Railway **Variables** (especially `TOKEN_ENCRYPTION_KEY`) outside Railway.
