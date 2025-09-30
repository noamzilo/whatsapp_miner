from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, text
from sqlalchemy import pool

from alembic import context
from src.db.db_interface import DbInterface

# Import all model classes so they're registered with DbInterface.metadata
from src.db.models import *

config = context.config

def sanitize_env_var(name: str) -> str:
	value = os.getenv(name)
	if value is None:
		raise RuntimeError(f"Missing required environment variable: {name}")
	return value.replace('"', "")

# Prefer session pooler for migrations; fallback to pooled, then direct
db_url = os.getenv("SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER")
if not db_url:
	raise RuntimeError("SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER is required")
config.set_main_option("sqlalchemy.url", db_url)
print("🚀 Alembic connecting to:", db_url)

if config.config_file_name is not None:
	fileConfig(config.config_file_name)

target_metadata = DbInterface.metadata

def run_migrations_offline() -> None:
	"""Run migrations in 'offline' mode."""
	url = config.get_main_option("sqlalchemy.url")
	context.configure(
		url=url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
		version_table_schema="public",  # ensure alembic_version is in public
	)

	with context.begin_transaction():
		context.run_migrations()

def run_migrations_online() -> None:
	"""Run migrations in 'online' mode."""
	connectable = engine_from_config(
		config.get_section(config.config_ini_section, {}),
		prefix="sqlalchemy.",
		poolclass=pool.NullPool,
	)



	with connectable.connect() as connection:
		print("🔎 Connected URL:", connection.engine.url)
		result = connection.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();"))
		print("🔎 DB identity:", list(result))
		
		# Always work in public schema
		connection.execute(text("SET search_path TO public;"))
		connection.commit()
		
		context.configure(
			connection=connection,
			target_metadata=target_metadata,
			version_table_schema="public",  # ensure alembic_version is in public
		)

		with context.begin_transaction():
			context.run_migrations()



if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
