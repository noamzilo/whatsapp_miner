import os

# TODO this file is bad practice. don't need to load everything everywhere

def sanitize_env_var(name, default=None):
	value = os.getenv(name)
	if value is None and default is None:
		raise RuntimeError(f"Missing required environment variable: {name}")
	elif value is None:
		value = default
	value = value.replace('"', "")
	return value

instance_id = sanitize_env_var("GREEN_API_INSTANCE_ID")
api_token = sanitize_env_var("GREEN_API_INSTANCE_API_TOKEN")
database_url = sanitize_env_var("SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER")
# database_url = sanitize_env_var("SUPABASE_DATABASE_CONNECTION_STRING")

# Message classifier configuration
message_classifier_run_every_seconds_raw = sanitize_env_var("MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS")
message_classifier_run_every_seconds = int(message_classifier_run_every_seconds_raw)
groq_api_key = sanitize_env_var("GROQ_API_KEY")

# Feature flags
message_classifier_enabled_raw = sanitize_env_var("FEATURE_FLAG_MESSAGE_CLASSIFIER_ENABLED", "true")
message_classifier_enabled = message_classifier_enabled_raw.lower() in ("true", "1", "yes", "on")

message_miner_enabled_raw = sanitize_env_var("FEATURE_FLAG_MESSAGE_MINER_ENABLED", "true")
message_miner_enabled = message_miner_enabled_raw.lower() in ("true", "1", "yes", "on")