import os

# ---- Factory (parent) bot ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # token of the main "bot builder" bot

# ---- Admin access ----
# The FIRST person to ever send this as a command (e.g. /kd7d7) becomes the
# permanent admin — their numeric id gets stored in the database, so you
# never have to look up and set your own Telegram id by hand. Anyone else
# who sends the same command afterwards is silently ignored.
# You can still hard-pin a specific id via ADMIN_ID if you prefer the old
# behavior (0 = disabled, rely on the claim system instead).
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_SECRET_CODE = os.getenv("ADMIN_SECRET_CODE", "kd7d7")

# ---- Forced-join gate for the factory bot itself ----
# Channel username the user must join before using the bot. Set to "" to disable.
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "")

# ---- Limits / monetization ----
FREE_BOT_LIMIT = int(os.getenv("FREE_BOT_LIMIT", "3"))
PREMIUM_BOT_LIMIT = int(os.getenv("PREMIUM_BOT_LIMIT", "20"))
SUBSCRIPTION_STARS_PRICE = int(os.getenv("SUBSCRIPTION_STARS_PRICE", "150"))  # Telegram Stars (XTR)
SUBSCRIPTION_DAYS = int(os.getenv("SUBSCRIPTION_DAYS", "30"))

# ---- Storage ----
DB_PATH = os.getenv("DB_PATH", "botfactory.db")

# ---- Mini App (real colored buttons) ----
# Public HTTPS base URL of this deployment, e.g. https://yourapp.up.railway.app
# Telegram requires web_app buttons to point at an https:// URL — Railway
# gives you this automatically once the service is a "web" service (see Procfile).
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "").rstrip("/")
PORT = int(os.getenv("PORT", "8080"))

# ---- Support contact shown to users ----
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@alone_2026_4")
