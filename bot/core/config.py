"""Central configuration. Secrets come from the environment (or a local .env);
everything else (branding, links, prefix) lives here so it is defined once."""

import os


def _load_dotenv(path=".env"):
    """Minimal .env loader so secrets stay out of source (no extra dependency)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# --- Secrets (from environment) ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
TOPGG_TOKEN = os.environ.get("TOPGG_TOKEN", "")

# --- Bot settings ---
COMMAND_PREFIX = ";"
OWNER_ID = 678908396845400074
BOT_ID = 1285070559087951974

# --- Branding / links (single source of truth for a uniform look) ---
BRAND_COLOR = 0xF1C40F
ERROR_COLOR = 0xE74C3C
SUCCESS_COLOR = 0x2ECC71
FOOTER_TEXT = "Developed by fzng (fang)."
SUPPORT_SERVER = "https://discord.gg/3UpnJhjkKZ"
TOPGG_VOTE = f"https://top.gg/bot/{BOT_ID}/vote"
INVITE_URL = (
    f"https://discord.com/oauth2/authorize?client_id={BOT_ID}&permissions=563914173967424&integration_type=0&scope=bot"
)


def require_token():
    """Return the Discord token, failing fast with a clear message if unset."""
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in "
            "(or export DISCORD_TOKEN in the environment)."
        )
    return DISCORD_TOKEN
