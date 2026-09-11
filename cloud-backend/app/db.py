import os

from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _database_target():
    """Return the SQLAlchemy target without exposing credentials.

    Production Cloud Run deployments use the Cloud SQL Unix socket mounted at
    /cloudsql/<instance-connection-name>. Local development may still use an
    explicit DATABASE_URL or the SQLite fallback.
    """
    db_user = os.getenv("DB_USER", "").strip()
    db_pass = os.getenv("DB_PASS", "")
    db_name = os.getenv("DB_NAME", "").strip()
    socket_dir = os.getenv("INSTANCE_UNIX_SOCKET", "").strip()

    if db_user and db_pass and db_name and socket_dir:
        return URL.create(
            drivername="postgresql+psycopg",
            username=db_user,
            password=db_pass,
            database=db_name,
            query={"host": socket_dir},
        )

    return os.getenv("DATABASE_URL", "sqlite:///./mercy.db")


DATABASE_TARGET = _database_target()
IS_SQLITE = str(DATABASE_TARGET).startswith("sqlite")

engine_kwargs = {"pool_pre_ping": True}
if IS_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Keep a small bounded pool for Cloud Run so instance scaling does not
    # exhaust the Cloud SQL connection limit.
    engine_kwargs.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "2")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
    )

engine = create_engine(DATABASE_TARGET, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_state():
    """Return non-sensitive health metadata for the configured database."""
    socket_dir = os.getenv("INSTANCE_UNIX_SOCKET", "").strip()
    target = str(DATABASE_TARGET)
    if socket_dir:
        backend = "cloud-sql-postgresql"
        durable = True
    elif target.startswith("postgresql"):
        backend = "postgresql"
        durable = True
    elif target.startswith("sqlite"):
        backend = "sqlite"
        durable = "/tmp/" not in target.replace("\\", "/")
    else:
        backend = "other"
        durable = False

    reachable = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        reachable = True
    except Exception:
        reachable = False

    return {"backend": backend, "durable": durable, "reachable": reachable}
