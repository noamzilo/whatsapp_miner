import os

def sanitize_env_var(env_var):
	env_var = env_var.replace('"', "")
	return env_var

instance_id = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_ID"))
api_token = sanitize_env_var(os.getenv("GREEN_API_INSTANCE_API_TOKEN"))