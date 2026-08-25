# 🛡️ Telegram Link Filter Bot

A Telegram bot that **auto-deletes messages containing links** from non-admin/owner members in your channel or group.

Admin and Owner messages with links are always allowed.

---

## ✨ Features

- Auto-deletes messages with any URL (http, https, t.me, www.)
- Checks both message text and caption (photos, videos, documents)
- Detects hidden links in message entities (previews, text_link)
- Admin & Owner messages are exempt
- Logs every deleted message with user & chat info

---

## 🚀 Setup

### 1. Create your bot
1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot`, choose a name & username
3. Copy the **Bot Token** it gives you

### 2. Add bot to your channel
1. Open your channel → **Settings** → **Administrators** → **Add Administrator**
2. Search for your bot and add it
3. Give it **Delete Messages** permission ✅

### 3. Deploy (24/7)

#### Option A: Render (Recommended — Free)
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Set environment variable: `BOT_TOKEN` = your token
5. Deploy — it runs 24/7 on the free tier

#### Option B: Koyeb (Free)
1. Push to GitHub
2. Go to [koyeb.com](https://koyeb.com) → Create App
3. Connect repo, set `BOT_TOKEN` env var
4. Deploy

#### Option C: Local (for testing)
```bash
pip install -r requirements.txt
export BOT_TOKEN="your-token-here"
python telegram_link_filter_bot.py
```

---

## 📁 Project Structure

```
telegram_link_filter_bot.py   # Main bot script
requirements.txt              # Python dependencies
Dockerfile                    # For container deployment
```

---

## ⚠️ Important Notes

- Bot **must be an admin** in your channel with delete permission
- The bot only checks **new messages** (not edits)
- Works in both **channels** and **groups**

---

## 📄 License

MIT — Free to use and modify.
