"""Project constants"""

# Response keys
KEY_ERROR = "error"
KEY_MESSAGE = "message"
KEY_DROPLET_ID = "droplet_id"
KEY_IP_ADDRESS = "ip_address"
KEY_CONNECTED_CLIENTS = "connected_clients"
KEY_SHARE_TAG = "share_tag"
KEY_LAST_HEARTBEAT = "last_heartbeat"

# Error messages
ERROR_NO_ACTIVE_SESSION = "No active game session found for this user and game."
ERROR_DROPLET_NOT_FOUND_DB = "Droplet not found in database."
ERROR_DROPLET_NOT_FOUND_DO = "Droplet does not exist in DigitalOcean."
ERROR_TOKEN_NOT_SET = "DIGITALOCEAN_TOKEN is not set"
ERROR_TAG_NOT_SET = "DROPLET_TAG is not set"

# Warning messages
WARN_DROPLET_NOT_IN_DO = "Droplet {droplet_id} does not exist in DigitalOcean."
WARN_DROPLET_NOT_IN_DB = "Droplet {droplet_id} not found in the database."

# Success messages
MSG_SESSION_ENDED = "Game session ended and droplet released."
MSG_HEARTBEAT_UPDATED = "Heartbeat updated successfully."
