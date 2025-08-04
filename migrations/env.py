from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from src.db.db_interface import DbInterface

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Inject actual database URL from environment with same sanitization as the app
def sanitize_env_var(name):
    value = os.getenv(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.replace('"', "")

db_url = sanitize_env_var("SUPABASE_DATABASE_CONNECTION_STRING")
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
	fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = DbInterface.metadata


def run_migrations_offline() -> None:
	"""Run migrations in 'offline' mode."""
	url = config.get_main_option("sqlalchemy.url")
	context.configure(
		url=url,
		target_metadata=target_metadata,
		literal_binds=True,
		dialect_opts={"paramstyle": "named"},
		version_table_schema="public"
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
		# Set search path to public schema
		connection.execute("SET search_path TO public;")
		
		context.configure(
			connection=connection,
			target_metadata=target_metadata,
			version_table_schema="public"
		)

		with context.begin_transaction():
			context.run_migrations()


if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
