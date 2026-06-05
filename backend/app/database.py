from sqlmodel import create_engine, Session, SQLModel
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    from sqlalchemy import text
    with engine.begin() as conn:
        try:
            conn.execute(text("SELECT currency FROM account LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE account ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
            except Exception as e:
                print(f"Migration error: {e}")

