import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

from alembic import context
from task_api.infrastructure.persistence.models import Base

config = context.config
load_dotenv()
if config.config_file_name:
    fileConfig(config.config_file_name)
url = os.environ.get("DATABASE_URL")
if not url or not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("DATABASE_URL PostgreSQL com psycopg é obrigatória para migrações.")
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        hide_parameters=True,
    )
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
