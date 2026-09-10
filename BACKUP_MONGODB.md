# MongoDB backup & restore (Railway ContactBot)

Your app data lives in MongoDB: **owners**, **bots** (encrypted tokens), **bot_users**, **message maps**, **broadcasts**, **subscriptions**, **app_settings**, etc. If Railway deletes the project or the Mongo volume fails, you need a **dump outside Railway**.

## What to back up

| Store | Contents |
|--------|-----------|
| **MongoDB dump** | All business data (required) |
| **Railway Variables** (export/screenshot) | `MASTER_BOT_TOKEN`, `TOKEN_ENCRYPTION_KEY`, `WEBHOOK_SECRET`, `ADMIN_*` — **not** in Mongo |
| **`.env` / password manager** | Same secrets; without `TOKEN_ENCRYPTION_KEY`, old encrypted child tokens cannot be decrypted |

Back up **at least weekly** (or before big changes). Keep 2–3 copies (PC + cloud folder).

---

## Option A — `mongodump` (recommended)

Install [MongoDB Database Tools](https://www.mongodb.com/try/download/database-tools) (`mongodump`, `mongorestore`).

### 1. Get connection URI

**From Railway dashboard:** MongoDB service → **Variables** → copy `MONGO_URL` (or build from `MONGOUSER` / `MONGOPASSWORD` / `MONGOHOST`).

**From CLI** (project linked, service `MongoDB`):

```powershell
cd d:\python\Telegrambots\ContactBot
railway service link MongoDB
railway variable list --kv
```

Use the full `MONGO_URL` value. For dumps from your PC, the host must be reachable:

- Railway **public TCP proxy** (if enabled on MongoDB service), or  
- Run dump **inside** Railway (one-off job) with internal `mongodb.railway.internal`, or  
- Use **MongoDB Atlas** with a URI that works from anywhere (see [DEPLOY_ATLAS.md](DEPLOY_ATLAS.md)).

### 2. Export (Windows PowerShell)

```powershell
cd d:\python\Telegrambots\ContactBot
$uri = "mongodb://USER:PASS@HOST:PORT"   # or paste MONGO_URL
$db = "ChatReplyBot"
$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$out = "backups\dump_$stamp"
mongodump --uri="$uri" --db=$db --out=$out
Compress-Archive -Path $out -DestinationPath "$out.zip"
```

Or use the script:

```powershell
$env:MONGODB_URI = "your_mongo_url"
$env:MONGODB_DATABASE = "ChatReplyBot"
.\scripts\backup-mongo.ps1
```

Output: `backups/contactbot_YYYY-MM-DD_HHmm/` (and optional `.zip`).

### 3. Restore (new Railway, Atlas, or local Mongo)

```powershell
$uri = "mongodb://USER:PASS@NEW_HOST:PORT"
$db = "ChatReplyBot"
mongorestore --uri="$uri" --db=$db --drop backups\contactbot_2026-09-10_1200\contactbot
```

- `--drop` replaces existing collections in that database (use on empty/new DB).
- Point **contactbot** service `MONGODB_URI` + `MONGODB_DATABASE` at the new server → redeploy.

---

## Option B — MongoDB Atlas (backup-friendly)

Atlas **M0** free tier: manual `mongodump` anytime; **M10+** gets continuous cloud backups.

1. Move data: dump from Railway → `mongorestore` to Atlas (see [DEPLOY_ATLAS.md](DEPLOY_ATLAS.md)).
2. Set Railway `MONGODB_URI` to Atlas.
3. Schedule weekly `mongodump` from your PC against the Atlas URI.

If Railway is lost, create a new app service, set the **same Atlas URI**, redeploy — data is already safe.

---

## Option C — JSON export (single collection)

```powershell
mongoexport --uri="$uri" --db=ChatReplyBot --collection=bots --out=bots.json
```

Good for inspection; full restore is easier with `mongodump`.

---

## If Railway environment is lost

1. Create new Railway project (or use another host).
2. Restore MongoDB from latest dump (or keep using Atlas).
3. Set variables on **contactbot**: `MONGODB_URI`, `MONGODB_DATABASE`, `MASTER_BOT_TOKEN`, `REDIS_URL`, `WEBHOOK_HOST`, `WEBHOOK_SECRET`, `TOKEN_ENCRYPTION_KEY`, `SUPER_ADMIN_IDS`, `ADMIN_WEB_PASSWORD`, `ADMIN_WEB_SECRET`, `ENVIRONMENT=production`, etc.
4. Generate public domain → `WEBHOOK_HOST` → redeploy.
5. Telegram: master bot webhook updates on startup; child bots reload from DB if tokens were encrypted with the **same** `TOKEN_ENCRYPTION_KEY`.

---

## Do not commit backups

Add to `.gitignore` if needed:

```
backups/
*.dump
```

Never commit dumps (they contain encrypted tokens and user data).
