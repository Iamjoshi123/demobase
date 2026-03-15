"""Database engine and session management."""

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from app.config import settings

# SQLite needs check_same_thread=False for FastAPI
connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine_kwargs = {
    "echo": settings.is_dev,
    "connect_args": connect_args,
}

if "sqlite" in settings.database_url:
    # Live voice transcription can fan out concurrent short-lived sessions.
    # QueuePool causes avoidable starvation here; SQLite behaves better with NullPool.
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(
    settings.database_url,
    **engine_kwargs,
)


def create_db_and_tables():
    """Create all tables from SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_schema()


def get_session():
    """Dependency that yields a DB session."""
    with Session(engine) as session:
        yield session


def _ensure_sqlite_schema() -> None:
    if "sqlite" not in settings.database_url:
        return

    required_columns = {
        "workspaces": {
            "browser_auth_mode": "TEXT DEFAULT 'credentials'",
        },
        "sessions": {
            "live_status": "TEXT DEFAULT 'idle'",
            "active_recipe_id": "TEXT",
            "current_step_index": "INTEGER DEFAULT 0",
            "live_room_name": "TEXT",
            "live_participant_identity": "TEXT",
        },
        "v2_meeting_sessions": {
            "runtime_session_id": "TEXT",
            "active_recipe_id": "TEXT",
            "current_step_index": "INTEGER DEFAULT 0",
            "live_room_name": "TEXT",
            "live_participant_identity": "TEXT",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in required_columns.items():
            table_info = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            if not table_info:
                continue
            existing = {
                row[1]
                for row in table_info
            }
            for column_name, ddl in columns.items():
                if column_name in existing:
                    continue
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")
                )
