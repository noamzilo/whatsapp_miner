import os

def sanitize_env_var(name):
	value = os.getenv(name)
	if value is None:
		raise RuntimeError(f"Missing required environment variable: {name}")
	value = value.replace('"', "")
	return value

instance_id = sanitize_env_var("GREEN_API_INSTANCE_ID")
api_token = sanitize_env_var("GREEN_API_INSTANCE_API_TOKEN")
database_url = sanitize_env_var("SUPABASE_DATABASE_CONNECTION_STRING")

# Message classifier configuration
message_classifier_run_every_seconds_raw = sanitize_env_var("MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS")
message_classifier_run_every_seconds = 3000 if message_classifier_run_every_seconds_raw is None else int(message_classifier_run_every_seconds_raw)
groq_api_key = sanitize_env_var("GROQ_API_KEY")