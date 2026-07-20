"""Constants for the Amazon Kids integration."""

DOMAIN = "amazon_kids"

CONF_COOKIE = "cookie"
CONF_CSRF_TOKEN = "csrf_token"
CONF_CHILDREN = "children"
CONF_CHILD_NAME = "name"
CONF_CHILD_ID = "directed_id"
CONF_DEFAULT_PAUSE_MINUTES = "default_pause_minutes"

DEFAULT_PAUSE_MINUTES = 60

# Service for a per-press configurable duration.
SERVICE_PAUSE = "pause"
SERVICE_RESUME = "resume"
ATTR_MINUTES = "minutes"

# A large value used as the "pause until manually resumed" magnitude if a user
# picks a very long duration. Amazon may cap this; documented as such.
MAX_PAUSE_SECONDS = 24 * 3600
