import os

def sanitize_env_var(env_var):
	if env_var is None:
		raise RuntimeError("Missing required environment variable.")
	env_var = env_var.replace('"', "")
	return env_var

instance_id = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_ID"))
api_token = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_API_TOKEN"))
database_url = sanitize_env_var(os.environ["SUPABASE_DATABASE_CONNECTION_STRING"])

# Message classifier configuration
message_classifier_run_every_seconds = int(os.getenv("MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS", "600"))
groq_api_key = sanitize_env_var(os.getenv("GROQ_API_KEY"))