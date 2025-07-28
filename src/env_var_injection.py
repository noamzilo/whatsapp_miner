import os

def sanitize_env_var(env_var):
	if env_var is None:
		raise RuntimeError("Missing required environment variable.")
	env_var = env_var.replace('"', "")
	return env_var

instance_id = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_ID"))
api_token = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_API_TOKEN"))
database_url = os.environ["SUPABASE_DATABASE_CONNECTION_STRING"]