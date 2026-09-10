# Deploy ContactBot on Railway

## 1. Create project and services

1. In [ContactBot](.) directory: `railway login` (if needed), then `railway init`.
2. In Railway dashboard, add **MongoDB** and **Redis** to the same project.
3. **MongoDB disk:** MongoDB requires at least **512 MB** free on its volume. If deploy logs show `OutOfDiskSpace` / `code 14031`, open the **MongoDB** service → **Volumes** → increase size (e.g. 1 GB), then redeploy **contactbot**.
3. On the **ContactBot** service, set variables (see below). Reference plugin URLs, e.g. `${{MongoDB.MONGO_URL}}` — use the exact names Railway shows for your plugins.

## 2. Required variables (ContactBot service)

| Variable | Value |
|----------|--------|
| `MASTER_BOT_TOKEN` | From @BotFather |
| `MONGODB_URI` | From MongoDB service |
| `MONGODB_DATABASE` | `contactbot` |
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

Or connect GitHub for automatic deploys.

## 5. Verify

- `curl https://YOUR-SERVICE.up.railway.app/health`
- `https://YOUR-SERVICE.up.railway.app/admin`
- Master bot: `/start`, `/addbot`

Do **not** commit `.env` (see `.gitignore`).
