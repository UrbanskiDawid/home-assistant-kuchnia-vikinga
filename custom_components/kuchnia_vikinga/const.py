"""Constants for the Kuchnia Vikinga integration."""

DOMAIN = "kuchnia_vikinga"
TIME_ZONE = "Europe/Warsaw"

# Votes are kept locally in .storage, keyed by dish name.
STORAGE_KEY = f"{DOMAIN}.votes"
SIGNAL_VOTES = f"{DOMAIN}_votes_changed"
VOTES = ("up", "down")

CARD_URL = f"/{DOMAIN}/kuchnia-vikinga-card.js"
