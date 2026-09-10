# Fix OutOfDiskSpace (14031) with MongoDB Atlas (recommended on Railway Trial)

Railway's **500 MB** Mongo plugin leaves **< 512 MB free**, so MongoDB refuses index creation and the app crashes.

**Fastest fix without upgrading Railway:** use **MongoDB Atlas M0 (free)** for data; keep **Redis + contactbot** on Railway.

## 1. Create Atlas cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register) and create a **free M0** cluster.
2. **Database Access** → add a user (username + password).
3. **Network Access** → **Add IP Address** → **Allow Access from Anywhere** (`0.0.0.0/0`) so Railway can connect.

## 2. Connection string

1. **Database** → **Connect** → **Drivers** → copy the URI, e.g.  
   `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/`
2. Append database name:  
   `mongodb+srv://USER:PASS@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`

## 3. Set on Railway (contactbot service only)

In Railway → **contactbot** → **Variables**:

| Variable | Value |
|----------|--------|
| `MONGODB_URI` | Your Atlas URI (replace Railway `${{MongoDB.MONGO_URL}}`) |
| `MONGODB_DATABASE` | `ChatReplyBot` |

You can **remove or stop** the Railway **MongoDB** service to save usage (optional).

Redeploy **contactbot**.

## 4. Verify

- `https://YOUR-APP.up.railway.app/health` → OK  
- Telegram master bot `/start`

Indexes are created automatically on startup when Atlas has enough space.
