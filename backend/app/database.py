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
        # Migrate: add currency column if missing
        try:
            conn.execute(text("SELECT currency FROM account LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE account ADD COLUMN currency VARCHAR DEFAULT 'INR'"))
            except Exception as e:
                print(f"Migration error: {e}")

    # Auto-replay: populate Holding table if empty but transactions exist
    from app.models import Holding, Transaction
    from sqlmodel import Session, select
    with Session(engine) as session:
        has_holdings = session.exec(select(Holding).limit(1)).first()
        has_transactions = session.exec(select(Transaction).limit(1)).first()
        if not has_holdings and has_transactions:
            from app.services.transaction_service import replay_all_holdings
            replay_all_holdings(session)

